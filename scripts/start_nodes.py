import sys
import os
import subprocess
import time
from pathlib import Path

NODES = [
    {"id": "node-01", "port": 5001, "dir": "storage/node1", "zone": "Zone-A"},
    {"id": "node-02", "port": 5002, "dir": "storage/node2", "zone": "Zone-A"},
    {"id": "node-03", "port": 5003, "dir": "storage/node3", "zone": "Zone-A"},
    {"id": "node-04", "port": 5004, "dir": "storage/node4", "zone": "Zone-B"},
    {"id": "node-05", "port": 5005, "dir": "storage/node5", "zone": "Zone-B"},
    {"id": "node-06", "port": 5006, "dir": "storage/node6", "zone": "Zone-B"},
]


def start_all_nodes():
    processes = []
    base_dir = Path(__file__).resolve().parent.parent

    for n in NODES:
        node_dir = base_dir / n["dir"]
        node_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "app.node_daemon.server",
            "--node-id",
            n["id"],
            "--port",
            str(n["port"]),
            "--dir",
            str(node_dir),
            "--zone",
            n["zone"],
        ]
        p = subprocess.Popen(cmd, cwd=str(base_dir))
        processes.append((n, p))
        print(f"Started {n['id']} on port {n['port']} ({n['zone']}) in {n['dir']} (PID: {p.pid})")

    print("\nAll 6 storage nodes running.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping storage nodes...")
        for n, p in processes:
            p.terminate()
            p.wait()
        print("All storage nodes stopped.")


if __name__ == "__main__":
    start_all_nodes()
