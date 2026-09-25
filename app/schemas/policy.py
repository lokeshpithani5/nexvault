from typing import Optional
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
    availability_mode: str  # 'DURABILITY_FIRST', 'AVAILABILITY_FIRST'
    description: Optional[str] = None


class PolicyCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=64)
    type: str = Field(default="REPLICATION", pattern="^(REPLICATION|ERASURE_CODING)$")
    replication_factor: int = Field(default=3, ge=1, le=6)
    data_shards: int = Field(default=4, ge=1, le=4)
    parity_shards: int = Field(default=2, ge=1, le=2)
    min_write_quorum: int = Field(default=2, ge=1, le=6)
    min_read_quorum: int = Field(default=1, ge=1, le=6)
    availability_mode: str = Field(default="DURABILITY_FIRST", pattern="^(DURABILITY_FIRST|AVAILABILITY_FIRST)$")
    description: Optional[str] = None


class PolicyUpdateRequest(BaseModel):
    description: Optional[str] = None
    min_write_quorum: Optional[int] = Field(None, ge=1, le=6)
    min_read_quorum: Optional[int] = Field(None, ge=1, le=6)
    availability_mode: Optional[str] = Field(None, pattern="^(DURABILITY_FIRST|AVAILABILITY_FIRST)$")
    replication_factor: Optional[int] = Field(None, ge=1, le=6)
