from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ObjectReplica(Base, TimestampMixin):
    __tablename__ = "object_replicas"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version_id = Column(String(36), ForeignKey("object_versions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(36), ForeignKey("storage_nodes.id", ondelete="RESTRICT"), nullable=False)
    chunk_index = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="HEALTHY", nullable=False)  # 'HEALTHY', 'CORRUPTED', 'MISSING', 'SYNCING'
    stored_checksum = Column(String(64), nullable=False)
    last_verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("version_id", "node_id", "chunk_index", name="uq_version_node_chunk"),
    )

    version = relationship("ObjectVersion", back_populates="replicas")
    node = relationship("StorageNode", back_populates="replicas")
