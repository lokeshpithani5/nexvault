from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, BigInteger, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Object(Base, TimestampMixin):
    __tablename__ = "objects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    bucket_id = Column(String(36), ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(1024), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("bucket_id", "key", name="uq_bucket_key"),
    )

    bucket = relationship("Bucket", back_populates="objects")
    versions = relationship("ObjectVersion", back_populates="object", cascade="all, delete-orphan", order_by="desc(ObjectVersion.version_num)")


class ObjectVersion(Base, TimestampMixin):
    __tablename__ = "object_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    object_id = Column(String(36), ForeignKey("objects.id", ondelete="CASCADE"), nullable=False)
    version_num = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    content_type = Column(String(128), default="application/octet-stream", nullable=False)
    is_tombstone = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("object_id", "version_num", name="uq_object_version_num"),
    )

    object = relationship("Object", back_populates="versions")
    replicas = relationship("ObjectReplica", back_populates="version", cascade="all, delete-orphan")
    repair_jobs = relationship("RepairJob", back_populates="version", cascade="all, delete-orphan")
