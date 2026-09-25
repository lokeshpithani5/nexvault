from datetime import datetime
from pydantic import BaseModel, ConfigDict


class StorageNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    host: str
    port: int
    zone: str
    status: str
    is_simulated_partitioned: bool
    total_capacity_bytes: int
    used_capacity_bytes: int
    last_heartbeat: datetime


class ClusterStatsResponse(BaseModel):
    total_nodes: int
    healthy_nodes: int
    degraded_nodes: int
    failed_nodes: int
    total_capacity_bytes: int
    used_capacity_bytes: int
    utilization_percent: float
    total_objects: int
    total_replicas: int
    active_repair_jobs: int
