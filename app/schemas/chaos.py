from typing import List, Optional
from pydantic import BaseModel


class NodeFailRequest(BaseModel):
    node_id: str
    action: str = "FAIL"  # 'FAIL', 'STOP'


class NodeRestoreRequest(BaseModel):
    node_id: str


class CorruptReplicaRequest(BaseModel):
    replica_id: Optional[str] = None
    node_id: Optional[str] = None
    random: bool = False


class NetworkPartitionRequest(BaseModel):
    node_ids: List[str]
    partitioned: bool = True


class ChaosOperationResponse(BaseModel):
    success: bool
    operation: str
    message: str
    affected_entities: dict = {}
