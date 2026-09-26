"""
NEXVAULT Realistic Demo Data Seeder
Populates buckets, files of multiple formats, versions, and events
for a rich initial demonstration.
"""

import sys
import os
import asyncio
import hashlib
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bucket import Bucket
from backend.app.services.data_pipeline import write_object
from backend.app.services.event_logger import log_event


DEMO_FILES = [
    {
        "bucket": "production-data",
        "key": "finance/q3_earnings_audit_2026.pdf",
        "content_type": "application/pdf",
        "data": b"%PDF-1.4\n1 0 obj << /Title (Q3 2026 Financial Durability Report) >> endobj\n" + (b"CONFIDENTIAL_LEDGER_DATA_NEXVAULT_RESILIENCE_OK\n" * 60),
    },
    {
        "bucket": "production-data",
        "key": "kubernetes/cluster_state_backup.json",
        "content_type": "application/json",
        "data": b'{"cluster": "nexvault-k8s-prod", "replicas": 3, "nodes": ["node-1", "node-2", "node-4"], "resilient": true, "timestamp": "2026-09-26T00:00:00Z"}' * 20,
    },
    {
        "bucket": "production-data",
        "key": "architecture/distributed_system_spec.md",
        "content_type": "text/markdown",
        "data": b"# NEXVAULT Distributed Storage Specification\n\n- Fault tolerance across independently failing storage nodes.\n- Zone-aware placement (Zone A: 5001-5003, Zone B: 5004-5006).\n- Cryptographic SHA-256 self-healing on silent bit-rot.\n" * 15,
    },
    {
        "bucket": "analytics-logs",
        "key": "telemetry/stream_events_2026_09.log",
        "content_type": "text/plain",
        "data": (b"2026-09-26 02:00:00 INFO [IngestWorker] 140,290 events ingested successfully.\n" * 80),
    },
    {
        "bucket": "analytics-logs",
        "key": "metrics/recovery_benchmark_results.csv",
        "content_type": "text/csv",
        "data": b"test_id,nodes_failed,recovery_time_ms,bytes_restored,success\n1,1,412,45000,true\n2,1,388,45000,true\n3,2,820,90000,true\n",
    },
]


async def seed_data():
    print("🌱 Seeding realistic demonstration objects into NEXVAULT...")
    async with AsyncSessionLocal() as session:
        for file_spec in DEMO_FILES:
            b_name = file_spec["bucket"]
            b_stmt = select(Bucket).where(Bucket.name == b_name)
            bucket = (await session.execute(b_stmt)).scalar_one_or_none()
            if not bucket:
                continue

            try:
                v = await write_object(
                    session,
                    bucket=bucket,
                    key=file_spec["key"],
                    data=file_spec["data"],
                    content_type=file_spec["content_type"],
                )
                print(f"  ✓ Uploaded '{b_name}/{file_spec['key']}' (v{v.version_num}, {v.size_bytes} bytes, {len(v.replicas)} replicas)")
            except Exception as e:
                print(f"  ⚠️ Error writing {file_spec['key']}: {e}")

    print("✅ Demo objects and replicas successfully populated!")


if __name__ == "__main__":
    asyncio.run(seed_data())
