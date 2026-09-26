"""
NEXVAULT Cluster Terminator
Stops all storage nodes and the coordinator process.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent.resolve()
COORD_PID_FILE = ROOT_DIR / "coordinator_pid.json"


def main():
    print("🛑 Shutting down NEXVAULT cluster...")

    # Stop Coordinator
    if COORD_PID_FILE.exists():
        try:
            data = json.loads(COORD_PID_FILE.read_text())
            pid = data.get("pid")
            if pid:
                print(f"  Stopping Coordinator [PID {pid}]...")
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                else:
                    os.kill(pid, 9)
            COORD_PID_FILE.unlink()
        except Exception:
            pass

    # Stop port 8000 on Windows
    if sys.platform == "win32":
        cmd = 'powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"'
        subprocess.run(cmd, shell=True, capture_output=True)

    # Stop 6 nodes
    nodes_script = ROOT_DIR / "scripts" / "cluster_nodes.py"
    subprocess.run([sys.executable, str(nodes_script), "stop"])

    print("✅ All NEXVAULT processes terminated successfully.")


if __name__ == "__main__":
    main()
