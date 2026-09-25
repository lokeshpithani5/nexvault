from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.core.database import Base
from app.models.base import generate_uuid


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    severity = Column(String(16), default="INFO", nullable=False)  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    category = Column(String(32), index=True, nullable=False)      # 'NODE', 'REPLICA', 'INTEGRITY', 'REPAIR', 'CHAOS', 'AUTH'
    message = Column(String(512), nullable=False)
    details_json = Column(JSON, default=dict, nullable=False)
