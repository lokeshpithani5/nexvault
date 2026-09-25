from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    event_type: Optional[str] = None
    severity: str
    category: str
    message: str
    node_id: Optional[str] = None
    object_key: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    details_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_extracted_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__") or isinstance(data, dict):
            details = getattr(data, "details_json", None) if not isinstance(data, dict) else data.get("details_json", {})
            if details is None:
                details = {}
            node = details.get("node_id") or details.get("node_name") or details.get("node")
            obj = details.get("object_key") or details.get("key")

            if not isinstance(data, dict):
                return {
                    "id": getattr(data, "id", None),
                    "timestamp": getattr(data, "timestamp", None),
                    "event_type": getattr(data, "event_type", None) or details.get("event_type"),
                    "severity": getattr(data, "severity", "INFO"),
                    "category": getattr(data, "category", "GENERAL"),
                    "message": getattr(data, "message", ""),
                    "node_id": getattr(data, "node_id", node),
                    "object_key": getattr(data, "object_key", obj),
                    "details": details,
                    "details_json": details,
                }
            else:
                data.setdefault("details", details)
                data.setdefault("details_json", details)
                if "node_id" not in data or data["node_id"] is None:
                    data["node_id"] = node
                if "object_key" not in data or data["object_key"] is None:
                    data["object_key"] = obj
                if not data.get("event_type"):
                    data["event_type"] = details.get("event_type")
        return data


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    database: str
    storage_nodes: Dict[str, Any]
