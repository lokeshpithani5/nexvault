from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    replication_factor: int
    data_shards: int
    parity_shards: int
    min_write_quorum: int
    min_read_quorum: int
    description: Optional[str] = None


class BucketCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=63, pattern="^[a-z0-9][a-z0-9-.]*[a-z0-9]$")
    policy_id: Optional[str] = None  # If omitted, default RF=3 policy is used


class BucketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    owner_id: str
    policy_id: str
    created_at: datetime
    policy: Optional[PolicyResponse] = None
    object_count: int = 0
    total_size_bytes: int = 0


class ReplicaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str
    node_id: str
    node_name: Optional[str] = None
    node_port: Optional[int] = None
    node_zone: Optional[str] = None
    chunk_index: int
    status: str
    stored_checksum: str
    last_verified_at: datetime


class ObjectVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_num: int
    size_bytes: int
    sha256_checksum: str
    content_type: str
    is_tombstone: bool
    created_at: datetime
    replicas: List[ReplicaResponse] = []


class ObjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bucket_id: str
    key: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    current_version: Optional[ObjectVersionResponse] = None


class ObjectDetailResponse(BaseModel):
    id: str
    bucket_id: str
    bucket_name: str
    key: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    policy: PolicyResponse
    current_version: Optional[ObjectVersionResponse] = None
    versions: List[ObjectVersionResponse] = []
