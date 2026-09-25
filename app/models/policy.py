from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, nullable=False)
    type = Column(String(32), default="REPLICATION", nullable=False)  # 'REPLICATION', 'ERASURE_CODING'
    replication_factor = Column(Integer, default=3, nullable=False)
    data_shards = Column(Integer, default=4, nullable=False)
    parity_shards = Column(Integer, default=2, nullable=False)
    min_write_quorum = Column(Integer, default=2, nullable=False)
    min_read_quorum = Column(Integer, default=1, nullable=False)
    description = Column(Text, nullable=True)

    buckets = relationship("Bucket", back_populates="policy")
