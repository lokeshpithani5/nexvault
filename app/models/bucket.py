from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Bucket(Base, TimestampMixin):
    __tablename__ = "buckets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, index=True, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    owner = relationship("User", back_populates="buckets")
    policy = relationship("Policy", back_populates="buckets")
    objects = relationship("Object", back_populates="bucket", cascade="all, delete-orphan")
