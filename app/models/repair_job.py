from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid


class RepairJob(Base):
    __tablename__ = "repair_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version_id = Column(String(36), ForeignKey("object_versions.id", ondelete="CASCADE"), nullable=False)
    source_node_id = Column(String(36), ForeignKey("storage_nodes.id", ondelete="SET NULL"), nullable=True)
    target_node_id = Column(String(36), ForeignKey("storage_nodes.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(32), default="PENDING", nullable=False)  # 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    trigger_reason = Column(String(128), nullable=False)            # 'NODE_FAILURE', 'BITROT_DETECTED', 'REBALANCE'
    bytes_repaired = Column(BigInteger, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    version = relationship("ObjectVersion", back_populates="repair_jobs")
    source_node = relationship("StorageNode", foreign_keys=[source_node_id], back_populates="source_repairs")
    target_node = relationship("StorageNode", foreign_keys=[target_node_id], back_populates="target_repairs")
