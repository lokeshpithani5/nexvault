"""
Bucket model for logical namespace & durability policies
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Bucket(Base):
    __tablename__ = "buckets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), unique=True, index=True, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    replication_factor = Column(Integer, default=3, nullable=False)
    durability_policy = Column(String(32), default="REPLICATION_3X", nullable=False)  # REPLICATION_2X, REPLICATION_3X, EC_4_2
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="buckets")
    objects = relationship("ObjectEntity", back_populates="bucket", cascade="all, delete-orphan")
