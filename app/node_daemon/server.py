import os
import sys
import hashlib
import json
import argparse
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

app = FastAPI(title="NEXVAULT Storage Node Daemon")

STORAGE_DIR: Path = Path("./storage/node_default")
NODE_ID: str = "node-unknown"
NODE_PORT: int = 5000
NODE_ZONE: str = "Zone-A"


def get_paths(replica_id: str):
    bin_path = STORAGE_DIR / f"{replica_id}.bin"
    meta_path = STORAGE_DIR / f"{replica_id}.meta"
    return bin_path, meta_path


@app.get("/health")
async def health():
    total_bytes = 10 * 1024 * 1024 * 1024  # 10 GiB nominal
    used_bytes = sum(f.stat().st_size for f in STORAGE_DIR.glob("*.bin") if f.is_file())
    free_bytes = max(0, total_bytes - used_bytes)
    return {
        "status": "HEALTHY",
        "node_id": NODE_ID,
        "port": NODE_PORT,
        "zone": NODE_ZONE,
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "chunks_count": len(list(STORAGE_DIR.glob("*.bin"))),
    }


@app.put("/chunks/{replica_id}")
async def put_chunk(replica_id: str, request: Request):
    """Store raw chunk bytes and compute SHA-256."""
    data = await request.body()
    bin_path, meta_path = get_paths(replica_id)

    # Compute SHA-256
    sha256 = hashlib.sha256(data).hexdigest()
    size = len(data)

    # Atomic write to temporary file then replace
    temp_path = STORAGE_DIR / f"{replica_id}.tmp"
    with open(temp_path, "wb") as f:
        f.write(data)
    if os.path.exists(bin_path):
        os.remove(bin_path)
    os.rename(temp_path, bin_path)

    # Write metadata
    meta = {
        "replica_id": replica_id,
        "size": size,
        "sha256": sha256,
        "node_id": NODE_ID,
        "port": NODE_PORT,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"stored": True, "replica_id": replica_id, "size": size, "sha256": sha256},
    )


@app.get("/chunks/{replica_id}")
async def get_chunk(replica_id: str):
    """Retrieve raw chunk bytes and verify checksum."""
    bin_path, meta_path = get_paths(replica_id)
    if not bin_path.exists():
        raise HTTPException(status_code=404, detail="Chunk replica not found")

    with open(bin_path, "rb") as f:
        data = f.read()

    calc_sha256 = hashlib.sha256(data).hexdigest()

    stored_sha256 = calc_sha256
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                stored_sha256 = meta.get("sha256", calc_sha256)
        except Exception:
            pass

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "X-Checksum-SHA256": calc_sha256,
            "X-Stored-SHA256": stored_sha256,
            "Content-Length": str(len(data)),
        },
    )


@app.head("/chunks/{replica_id}")
async def head_chunk(replica_id: str):
    """Check chunk presence and metadata."""
    bin_path, meta_path = get_paths(replica_id)
    if not bin_path.exists():
        raise HTTPException(status_code=404, detail="Chunk replica not found")

    size = bin_path.stat().st_size
    sha256 = "unknown"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                sha256 = meta.get("sha256", "unknown")
        except Exception:
            pass

    return Response(
        status_code=status.HTTP_200_OK,
        headers={
            "Content-Length": str(size),
            "X-Checksum-SHA256": sha256,
        },
    )


@app.delete("/chunks/{replica_id}")
async def delete_chunk(replica_id: str):
    """Delete chunk and associated metadata from disk."""
    bin_path, meta_path = get_paths(replica_id)
    deleted = False
    if bin_path.exists():
        os.remove(bin_path)
        deleted = True
    if meta_path.exists():
        os.remove(meta_path)
    return {"deleted": deleted, "replica_id": replica_id}


@app.post("/chunks/{replica_id}/corrupt")
async def corrupt_chunk(replica_id: str):
    """Chaos endpoint: deliberately flip bytes in chunk to simulate disk bitrot."""
    bin_path, _ = get_paths(replica_id)
    if not bin_path.exists():
        raise HTTPException(status_code=404, detail="Chunk not found to corrupt")

    with open(bin_path, "r+b") as f:
        data = bytearray(f.read())
        if len(data) > 0:
            # Corrupt the first byte
            data[0] = (data[0] ^ 0xFF)
            f.seek(0)
            f.write(data)
            f.truncate()

    return {"corrupted": True, "replica_id": replica_id}


def run_daemon(node_id: str, port: int, storage_dir: str, zone: str):
    global STORAGE_DIR, NODE_ID, NODE_PORT, NODE_ZONE
    NODE_ID = node_id
    NODE_PORT = port
    NODE_ZONE = zone
    STORAGE_DIR = Path(storage_dir)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXVAULT Storage Node Daemon")
    parser.add_argument("--node-id", type=str, required=True, help="Storage Node ID (e.g. node-01)")
    parser.add_argument("--port", type=int, required=True, help="Port (5001-5006)")
    parser.add_argument("--dir", type=str, required=True, help="Isolated storage directory path")
    parser.add_argument("--zone", type=str, default="Zone-A", help="Zone (Zone-A or Zone-B)")
    args = parser.parse_args()

    run_daemon(args.node_id, args.port, args.dir, args.zone)
