"""
NEXVAULT Full Cluster Orchestrator
Launches the 6 autonomous storage nodes and the FastAPI Control Plane Coordinator.
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent.resolve()
COORD_PID_FILE = ROOT_DIR / "coordinator_pid.json"


def start_coordinator() -> int:
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--log-level", "warning",
    ]
    log_file = ROOT_DIR / "coordinator.log"
    log_fp = open(log_file, "a")

    if sys.platform == "win32":
        proc = subprocess.Popen(
            cmd,
            stdout=log_fp,
            stderr=log_fp,
            cwd=str(ROOT_DIR),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fp,
            stderr=log_fp,
            cwd=str(ROOT_DIR),
            preexec_fn=os.setsid,
        )

    COORD_PID_FILE.write_text(json.dumps({"pid": proc.pid}, indent=2))
    return proc.pid


def check_coordinator_health() -> bool:
    try:
        url = "http://127.0.0.1:8000/"
        req = urllib.request.Request(url, headers={"User-Agent": "NexVault-Launcher"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    print("=" * 65)
    print("             NEXVAULT CLUSTER ORCHESTRATOR")
    print("             Storage that survives failure.")
    print("=" * 65)

    # 1. Start 6 storage nodes
    nodes_script = ROOT_DIR / "scripts" / "cluster_nodes.py"
    subprocess.run([sys.executable, str(nodes_script), "start"], check=True)

    # 2. Check / Start Coordinator
    if check_coordinator_health():
        print("⚡ Coordinator is already RUNNING on http://127.0.0.1:8000")
    else:
        print("🚀 Starting Control Plane Coordinator (FastAPI on Port 8000)...")
        pid = start_coordinator()
        print(f"  ✓ Spawned Coordinator [PID {pid}]")

        print("⏳ Waiting for Coordinator to initialize database & background loops...")
        for _ in range(15):
            time.sleep(0.5)
            if check_coordinator_health():
                break

    if check_coordinator_health():
        print("\n" + "=" * 65)
        print("✅ NEXVAULT CLUSTER IS FULLY OPERATIONAL!")
        print("=" * 65)
        print("📡 Control Plane Coordinator : http://127.0.0.1:8000")
        print("📖 Interactive Swagger API   : http://127.0.0.1:8000/docs")
        print("⚡ Storage Nodes (Zone A)    : http://127.0.0.1:5001, :5002, :5003")
        print("⚡ Storage Nodes (Zone B)    : http://127.0.0.1:5004, :5005, :5006")
        print("🖥️  Frontend Application       : cd frontend && npm run dev")
        print("-" * 65)
        print("👤 Demo User Account        : demo@nexvault.io  / demo123")
        print("🛡️  Admin Account             : admin@nexvault.io / admin123")
        print("=" * 65 + "\n")
    else:
        print("⚠️ Coordinator initialization timed out. Check coordinator.log for details.")


if __name__ == "__main__":
    main()
