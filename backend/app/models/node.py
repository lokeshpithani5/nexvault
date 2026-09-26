"""
StorageNode model for Data Plane registry & topology tracking
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class StorageNode(Base):
    __tablename__ = "storage_nodes"

    id = Column(String(32), primary_key=True)  # e.g. "node-1"
    name = Column(String(64), nullable=False)
    host = Column(String(128), default="127.0.0.1", nullable=False)
    port = Column(Integer, nullable=False)
    zone = Column(String(16), nullable=False)  # "ZONE_A" or "ZONE_B"
    status = Column(String(32), default="HEALTHY", nullable=False)  # HEALTHY, DEGRADED, FAILED, RECOVERING
    is_simulated_partitioned = Column(Boolean, default=False, nullable=False)
    capacity_bytes = Column(BigInteger, default=10 * 1024 * 1024 * 1024, nullable=False)  # 10 GB
    used_bytes = Column(BigInteger, default=0, nullable=False)
    replica_count = Column(Integer, default=0, nullable=False)
    last_heartbeat_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    replicas = relationship("ObjectReplica", back_populates="node")
