"""
Object, ObjectVersion, and ObjectReplica models
Supports full immutable versioning, deletion tombstones, and physical replica tracking.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class ObjectEntity(Base):
    __tablename__ = "objects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bucket_id = Column(String(36), ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(1024), index=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # True if latest version is a tombstone
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("bucket_id", "key", name="uq_bucket_key"),
    )

    bucket = relationship("Bucket", back_populates="objects")
    versions = relationship("ObjectVersion", back_populates="object_entity", cascade="all, delete-orphan", order_by="desc(ObjectVersion.version_num)")


class ObjectVersion(Base):
    __tablename__ = "object_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    object_id = Column(String(36), ForeignKey("objects.id", ondelete="CASCADE"), nullable=False)
    version_num = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    content_type = Column(String(128), default="application/octet-stream", nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    is_tombstone = Column(Boolean, default=False, nullable=False)  # Soft-deletion tombstone
    storage_policy = Column(String(32), default="REPLICATION_3X", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("object_id", "version_num", name="uq_object_version_num"),
    )

    object_entity = relationship("ObjectEntity", back_populates="versions")
    replicas = relationship("ObjectReplica", back_populates="version", cascade="all, delete-orphan")
    repair_jobs = relationship("RepairJob", back_populates="version", cascade="all, delete-orphan")


class ObjectReplica(Base):
    __tablename__ = "object_replicas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id = Column(String(36), ForeignKey("object_versions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(32), ForeignKey("storage_nodes.id"), nullable=False)
    shard_index = Column(Integer, default=0, nullable=False)  # 0 for full replica, 0..N for EC
    blob_id = Column(String(128), nullable=False)  # Actual filename on storage node disk
    status = Column(String(32), default="HEALTHY", nullable=False)  # HEALTHY, CORRUPTED, MISSING
    stored_checksum = Column(String(64), nullable=False)
    last_verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    error_detail = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("version_id", "node_id", "shard_index", name="uq_version_node_shard"),
    )

    version = relationship("ObjectVersion", back_populates="replicas")
    node = relationship("StorageNode", back_populates="replicas")
