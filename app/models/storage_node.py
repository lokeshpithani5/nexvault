from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class StorageNode(Base, TimestampMixin):
    __tablename__ = "storage_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, nullable=False)
    host = Column(String(128), default="127.0.0.1", nullable=False)
    port = Column(Integer, unique=True, nullable=False)
    zone = Column(String(32), nullable=False)  # 'Zone-A', 'Zone-B'
    status = Column(String(32), default="HEALTHY", nullable=False)  # 'HEALTHY', 'DEGRADED', 'FAILED', 'RECOVERING'
    is_simulated_partitioned = Column(Boolean, default=False, nullable=False)
    total_capacity_bytes = Column(BigInteger, default=10737418240, nullable=False)  # 10 GiB
    used_capacity_bytes = Column(BigInteger, default=0, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    replicas = relationship("ObjectReplica", back_populates="node")
    source_repairs = relationship("RepairJob", back_populates="source_node", foreign_keys="RepairJob.source_node_id")
    target_repairs = relationship("RepairJob", back_populates="target_node", foreign_keys="RepairJob.target_node_id")
