"""
SystemEvent model for structured distributed audit logging and live UI telemetry.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from backend.app.core.database import Base

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(64), index=True, nullable=False)
    # Types: NODE_HEARTBEAT_LOST, NODE_FAILED, NODE_RECOVERED, REPLICA_CORRUPTED,
    # REPAIR_TRIGGERED, REPAIR_COMPLETED, INTEGRITY_SCAN_COMPLETED, REBALANCE_TRIGGERED,
    # OBJECT_UPLOADED, OBJECT_DELETED
    severity = Column(String(16), default="INFO", nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    node_id = Column(String(32), nullable=True)
    object_id = Column(String(36), nullable=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
