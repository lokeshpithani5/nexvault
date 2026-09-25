from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    severity: str
    category: str
    message: str
    details_json: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    database: str
    storage_nodes: Dict[str, Any]
