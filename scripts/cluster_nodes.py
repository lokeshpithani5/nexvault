"""
NEXVAULT Cluster Nodes Manager
Spawns, monitors, and terminates 6 independent storage node processes.
Zone A: node-1 (5001), node-2 (5002), node-3 (5003)
Zone B: node-4 (5004), node-5 (5005), node-6 (5006)
"""

import sys
import os
import json
import time
import subprocess
import signal
from pathlib import Path
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent.resolve()
PID_FILE = ROOT_DIR / "nodes_pids.json"

NODE_SPECS = [
    {"id": "node-1", "port": 5001, "zone": "ZONE_A", "dir": "storage/node1"},
    {"id": "node-2", "port": 5002, "zone": "ZONE_A", "dir": "storage/node2"},
    {"id": "node-3", "port": 5003, "zone": "ZONE_A", "dir": "storage/node3"},
    {"id": "node-4", "port": 5004, "zone": "ZONE_B", "dir": "storage/node4"},
    {"id": "node-5", "port": 5005, "zone": "ZONE_B", "dir": "storage/node5"},
    {"id": "node-6", "port": 5006, "zone": "ZONE_B", "dir": "storage/node6"},
]


def load_pids():
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_pids(pids):
    PID_FILE.write_text(json.dumps(pids, indent=2))


def start_single_node(spec: dict) -> int:
    storage_path = ROOT_DIR / spec["dir"]
    storage_path.mkdir(parents=True, exist_ok=True)
    server_script = ROOT_DIR / "node_daemon" / "node_server.py"

    cmd = [
        sys.executable,
        str(server_script),
        "--node-id", spec["id"],
        "--port", str(spec["port"]),
        "--storage-dir", str(storage_path),
        "--zone", spec["zone"],
    ]

    log_file = ROOT_DIR / "storage" / f"{spec['id']}.log"
    log_fp = open(log_file, "a")

    # Start process without blocking
    if sys.platform == "win32":
        proc = subprocess.Popen(
            cmd,
            stdout=log_fp,
            stderr=log_fp,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        proc = subprocess.Popen(cmd, stdout=log_fp, stderr=log_fp, preexec_fn=os.setsid)

    return proc.pid


def stop_pid(pid: int):
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        pass


def check_node_health(port: int):
    try:
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "NexVault-Monitor"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                return True, data
    except Exception as e:
        return False, str(e)
    return False, "Unknown"


def start_all():
    pids = load_pids()
    print("🚀 Launching 6 independent NEXVAULT storage nodes...")
    for spec in NODE_SPECS:
        node_id = spec["id"]
        # Check if already running
        is_up, _ = check_node_health(spec["port"])
        if is_up:
            print(f"  ⚡ {node_id} (Port {spec['port']}) is already RUNNING.")
            continue

        pid = start_single_node(spec)
        pids[node_id] = pid
        print(f"  ✓ Spawned {node_id} (Port {spec['port']}, {spec['zone']}) [PID {pid}]")

    save_pids(pids)

    # Wait for nodes to warm up
    print("⏳ Waiting for health checks to pass...")
    all_healthy = False
    for attempt in range(10):
        time.sleep(0.5)
        statuses = [check_node_health(s["port"])[0] for s in NODE_SPECS]
        if all(statuses):
            all_healthy = True
            break

    if all_healthy:
        print("✅ All 6 storage nodes are ONLINE and HEALTHY!")
    else:
        print("⚠️ Some nodes may still be initializing. Run 'python scripts/cluster_nodes.py status'")


def stop_all():
    pids = load_pids()
    print("🛑 Stopping all NEXVAULT storage nodes...")
    for node_id, pid in list(pids.items()):
        print(f"  Terminating {node_id} [PID {pid}]...")
        stop_pid(pid)
    save_pids({})

    # Also kill any leftover processes on ports 5001-5006 on Windows
    if sys.platform == "win32":
        for spec in NODE_SPECS:
            port = spec["port"]
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"'
            subprocess.run(cmd, shell=True, capture_output=True)

    print("✅ All storage node processes terminated.")


def show_status():
    pids = load_pids()
    print("\n================ NEXVAULT DATA PLANE STATUS ================")
    print(f"{'NODE ID':<10} | {'ZONE':<8} | {'PORT':<6} | {'STATUS':<10} | {'CHUNKS':<8} | {'USED BYTES':<12}")
    print("-" * 65)
    for spec in NODE_SPECS:
        node_id = spec["id"]
        port = spec["port"]
        zone = spec["zone"]
        is_up, info = check_node_health(port)
        if is_up and isinstance(info, dict):
            status = info.get("status", "HEALTHY")
            chunks = info.get("chunk_count", 0)
            used = info.get("used_bytes", 0)
            print(f"{node_id:<10} | {zone:<8} | {port:<6} | {status:<10} | {chunks:<8} | {used:<12}")
        else:
            print(f"{node_id:<10} | {zone:<8} | {port:<6} | {'OFFLINE':<10} | {'-':<8} | {'-':<12}")
    print("============================================================\n")


def kill_node(node_id: str):
    pids = load_pids()
    spec = next((s for s in NODE_SPECS if s["id"] == node_id), None)
    if not spec:
        print(f"Error: Unknown node '{node_id}'")
        return

    pid = pids.get(node_id)
    if pid:
        stop_pid(pid)
        del pids[node_id]
        save_pids(pids)

    # Windows fallback
    if sys.platform == "win32":
        port = spec["port"]
        cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"'
        subprocess.run(cmd, shell=True, capture_output=True)

    print(f"💥 Node {node_id} (Port {spec['port']}) has been KILLED (Crash Simulated).")


def start_node(node_id: str):
    pids = load_pids()
    spec = next((s for s in NODE_SPECS if s["id"] == node_id), None)
    if not spec:
        print(f"Error: Unknown node '{node_id}'")
        return

    is_up, _ = check_node_health(spec["port"])
    if is_up:
        print(f"Node {node_id} is already running!")
        return

    pid = start_single_node(spec)
    pids[node_id] = pid
    save_pids(pids)
    time.sleep(1)
    is_up, _ = check_node_health(spec["port"])
    if is_up:
        print(f"🌱 Node {node_id} (Port {spec['port']}) RESTARTED successfully [PID {pid}].")
    else:
        print(f"⚠️ Node {node_id} spawned [PID {pid}], checking health...")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/cluster_nodes.py [start|stop|status|restart|kill-node <id>|start-node <id>]")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "start":
        start_all()
    elif action == "stop":
        stop_all()
    elif action == "restart":
        stop_all()
        time.sleep(1)
        start_all()
    elif action == "status":
        show_status()
    elif action == "kill-node" and len(sys.argv) >= 3:
        kill_node(sys.argv[2])
    elif action == "start-node" and len(sys.argv) >= 3:
        start_node(sys.argv[2])
    else:
        print(f"Unknown command: {action}")
