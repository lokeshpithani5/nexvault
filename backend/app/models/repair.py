"""
RepairJob and RebalanceTask models
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class RepairJob(Base):
    __tablename__ = "repair_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id = Column(String(36), ForeignKey("object_versions.id", ondelete="CASCADE"), nullable=False)
    source_node_id = Column(String(32), ForeignKey("storage_nodes.id"), nullable=True)
    target_node_id = Column(String(32), ForeignKey("storage_nodes.id"), nullable=True)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED
    trigger_reason = Column(String(64), nullable=False)  # NODE_FAILURE, BIT_ROT_DETECTED, REBALANCE
    bytes_recovered = Column(BigInteger, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    previous_replica_count = Column(Integer, default=0, nullable=False)
    resulting_replica_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    version = relationship("ObjectVersion", back_populates="repair_jobs")
    source_node = relationship("StorageNode", foreign_keys=[source_node_id])
    target_node = relationship("StorageNode", foreign_keys=[target_node_id])


class RebalanceTask(Base):
    __tablename__ = "rebalance_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_node_id = Column(String(32), ForeignKey("storage_nodes.id"), nullable=False)
    target_node_id = Column(String(32), ForeignKey("storage_nodes.id"), nullable=False)
    replica_id = Column(String(36), ForeignKey("object_replicas.id"), nullable=False)
    bytes_moved = Column(BigInteger, default=0, nullable=False)
    status = Column(String(32), default="COMPLETED", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
