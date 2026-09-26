"""
NEXVAULT Configuration & Constants
"""

import os
from pathlib import Path
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent.parent.parent.parent.resolve()

class Settings(BaseModel):
    PROJECT_NAME: str = "NEXVAULT"
    TAGLINE: str = "Storage that survives failure."
    VERSION: str = "1.0.0"
    
    # Control Plane Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite+aiosqlite:///{ROOT_DIR / 'nexvault_control_plane.db'}"
    )
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nexvault-super-secure-production-jwt-secret-key-3849102")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Storage Nodes
    DEFAULT_STORAGE_NODES: list[dict] = [
        {"id": "node-1", "name": "Storage Node 01", "host": "127.0.0.1", "port": 5001, "zone": "ZONE_A"},
        {"id": "node-2", "name": "Storage Node 02", "host": "127.0.0.1", "port": 5002, "zone": "ZONE_A"},
        {"id": "node-3", "name": "Storage Node 03", "host": "127.0.0.1", "port": 5003, "zone": "ZONE_A"},
        {"id": "node-4", "name": "Storage Node 04", "host": "127.0.0.1", "port": 5004, "zone": "ZONE_B"},
        {"id": "node-5", "name": "Storage Node 05", "host": "127.0.0.1", "port": 5005, "zone": "ZONE_B"},
        {"id": "node-6", "name": "Storage Node 06", "host": "127.0.0.1", "port": 5006, "zone": "ZONE_B"},
    ]
    
    # Durability Defaults
    DEFAULT_REPLICATION_FACTOR: int = 3
    DEFAULT_DURABILITY_POLICY: str = "REPLICATION_3X"
    
    # Heartbeat & Repair Engine
    HEARTBEAT_INTERVAL_SECONDS: float = 3.0
    NODE_OFFLINE_THRESHOLD_SECONDS: float = 8.0
    INTEGRITY_SCAN_INTERVAL_SECONDS: float = 30.0
    REBALANCE_IMBALANCE_THRESHOLD: float = 0.25 # 25% skew triggers rebalance

settings = Settings()
