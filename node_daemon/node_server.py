"""
NEXVAULT Storage Node Daemon
Independent, autonomous HTTP storage daemon for raw chunk blobs.
Runs independently on ports 5001-5006 with dedicated storage directories.
"""

import os
import sys
import time
import hashlib
import argparse
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import uvicorn

# Global state for chaos simulation and uptime tracking
START_TIME = time.time()
SIMULATED_STATE = "HEALTHY"  # HEALTHY, FAILED, PARTITIONED


def create_node_app(node_id: str, storage_dir: str, zone: str, port: int) -> FastAPI:
    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=f"NEXVAULT Node Daemon [{node_id}]",
        description=f"Autonomous storage node in {zone} running on port {port}",
        version="1.0.0",
    )

    # Middleware to simulate network partition or node failure
    @app.middleware("http")
    async def chaos_middleware(request: Request, call_next):
        # Don't block admin /chaos endpoints or health check so status can be recovered
        if request.url.path.startswith("/chaos") or request.url.path == "/health":
            return await call_next(request)

        global SIMULATED_STATE
        if SIMULATED_STATE == "FAILED":
            return Response(
                content=b'{"error": "Node is offline (SIMULATED_FAILED)"}',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json",
            )
        elif SIMULATED_STATE == "PARTITIONED":
            return Response(
                content=b'{"error": "Node unreachable due to network partition"}',
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                media_type="application/json",
            )

        return await call_next(request)

    @app.get("/health")
    async def get_health():
        """Node health, capacity, and chunk telemetry."""
        total_bytes = 0
        chunk_count = 0
        for entry in storage_path.glob("*.blob"):
            try:
                total_bytes += entry.stat().st_size
                chunk_count += 1
            except OSError:
                pass

        # Arbitrary virtual 10 GB limit per node for metrics
        virtual_capacity = 10 * 1024 * 1024 * 1024

        return {
            "node_id": node_id,
            "port": port,
            "zone": zone,
            "status": SIMULATED_STATE,
            "uptime_seconds": round(time.time() - START_TIME, 2),
            "capacity_bytes": virtual_capacity,
            "used_bytes": total_bytes,
            "available_bytes": max(0, virtual_capacity - total_bytes),
            "chunk_count": chunk_count,
            "storage_dir": str(storage_path.resolve()),
        }

    def resolve_blob_file(blob_id: str) -> Path:
        """
        Validates blob_id and prevents path traversal out of the storage directory.
        Rejects traversal patterns ('..', '/', '\\').
        """
        if not blob_id or ".." in blob_id or "/" in blob_id or "\\" in blob_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid blob_id: Path traversal rejected",
            )
        resolved = (storage_path / f"{blob_id}.blob").resolve()
        try:
            resolved.relative_to(storage_path.resolve())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid blob_id: Target path outside storage directory",
            )
        return resolved

    @app.put("/chunks/{blob_id:path}")
    async def put_chunk(blob_id: str, request: Request):
        """
        Store raw chunk bytes. Computes SHA-256 on the fly.
        Writes atomically to disk.
        """
        final_file = resolve_blob_file(blob_id)
        tmp_file = storage_path / f"{blob_id}.tmp"
        hasher = hashlib.sha256()
        total_size = 0

        try:
            with open(tmp_file, "wb") as f:
                async for chunk in request.stream():
                    if chunk:
                        f.write(chunk)
                        hasher.update(chunk)
                        total_size += len(chunk)

            # Atomic rename to prevent partial reads
            os.replace(tmp_file, final_file)
            calculated_hash = hasher.hexdigest()

            return {
                "blob_id": blob_id,
                "node_id": node_id,
                "size": total_size,
                "sha256": calculated_hash,
                "status": "STORED",
            }
        except HTTPException:
            raise
        except Exception as e:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to write chunk: {str(e)}")

    @app.get("/chunks/{blob_id:path}")
    async def get_chunk(blob_id: str):
        """
        Stream raw chunk bytes to caller with computed SHA-256 verification header.
        """
        file_path = resolve_blob_file(blob_id)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Chunk not found")

        # Compute on-disk hash to verify current integrity
        hasher = hashlib.sha256()
        file_size = file_path.stat().st_size
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        current_hash = hasher.hexdigest()

        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        return StreamingResponse(
            iterfile(),
            media_type="application/octet-stream",
            headers={
                "Content-Length": str(file_size),
                "X-Content-SHA256": current_hash,
                "X-Node-ID": node_id,
            },
        )

    @app.head("/chunks/{blob_id:path}")
    async def head_chunk(blob_id: str):
        """
        Check if chunk exists and return its size and on-disk SHA-256.
        """
        file_path = resolve_blob_file(blob_id)
        if not file_path.exists():
            return Response(status_code=404)

        hasher = hashlib.sha256()
        file_size = file_path.stat().st_size
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        current_hash = hasher.hexdigest()

        return Response(
            status_code=200,
            headers={
                "Content-Length": str(file_size),
                "X-Content-SHA256": current_hash,
                "X-Node-ID": node_id,
            },
        )

    @app.delete("/chunks/{blob_id:path}")
    async def delete_chunk(blob_id: str):
        """Remove chunk from disk."""
        file_path = resolve_blob_file(blob_id)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Chunk not found")

        try:
            file_path.unlink()
            return {"deleted": True, "blob_id": blob_id, "node_id": node_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete chunk: {str(e)}")

    @app.get("/chunks")
    async def list_chunks():
        """List all chunks with their sizes and verified on-disk hashes."""
        results = []
        for file_path in storage_path.glob("*.blob"):
            blob_id = file_path.name.replace(".blob", "")
            size = file_path.stat().st_size
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            results.append({
                "blob_id": blob_id,
                "size": size,
                "sha256": hasher.hexdigest(),
                "node_id": node_id,
            })
        return {"chunks": results, "total": len(results), "node_id": node_id}

    # ==================== CHAOS LAB ENDPOINTS ====================
    @app.post("/chaos/corrupt/{blob_id:path}")
    async def corrupt_chunk(blob_id: str):
        """
        Simulate Bit-Rot / Data Corruption.
        Mutates bytes on disk without updating external metadata,
        simulating silent hardware or media degradation.
        """
        file_path = resolve_blob_file(blob_id)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Chunk not found to corrupt")

        data = bytearray(file_path.read_bytes())
        if len(data) == 0:
            data.extend(b"CORRUPTED_PAYLOAD")
        else:
            # Invert bits on first bytes
            for i in range(min(8, len(data))):
                data[i] ^= 0xFF

        file_path.write_bytes(data)

        # Compute new corrupted hash
        corrupted_hash = hashlib.sha256(data).hexdigest()

        return {
            "corrupted": True,
            "blob_id": blob_id,
            "node_id": node_id,
            "new_corrupted_sha256": corrupted_hash,
            "message": "Bit-rot simulated successfully by flipping byte contents.",
        }

    @app.post("/chaos/set-state")
    async def set_state(request: Request):
        """Simulate node failure or network partition."""
        global SIMULATED_STATE
        payload = await request.json()
        target_state = payload.get("state", "HEALTHY").upper()
        if target_state not in ("HEALTHY", "FAILED", "PARTITIONED"):
            raise HTTPException(status_code=400, detail="Invalid state. Choose HEALTHY, FAILED, or PARTITIONED.")
        SIMULATED_STATE = target_state
        return {"node_id": node_id, "state": SIMULATED_STATE}

    return app


def main():
    parser = argparse.ArgumentParser(description="NEXVAULT Independent Storage Node Daemon")
    parser.add_argument("--node-id", required=True, help="Unique identifier, e.g. node-1")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on, e.g. 5001")
    parser.add_argument("--storage-dir", required=True, help="Directory path to store chunk files")
    parser.add_argument("--zone", default="ZONE_A", help="Availability zone (e.g. ZONE_A, ZONE_B)")
    args = parser.parse_args()

    app = create_node_app(
        node_id=args.node_id,
        storage_dir=args.storage_dir,
        zone=args.zone,
        port=args.port,
    )

    print(f"🚀 Starting NEXVAULT Node [{args.node_id}] in {args.zone} on http://127.0.0.1:{args.port}")
    print(f"📁 Storing chunks in {os.path.abspath(args.storage_dir)}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
