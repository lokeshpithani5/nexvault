import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "NEXVAULT Control Plane"
    APP_VERSION: str = "1.0.0"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # PostgreSQL Database URL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/nexvault_metadata"
    ENABLE_SQLITE_FALLBACK: bool = True
    SQLITE_FALLBACK_URL: str = "sqlite+aiosqlite:///./nexvault_metadata.db"

    # JWT Authentication
    SECRET_KEY: str = "nexvault-super-secret-development-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Initial Admin Seed
    INITIAL_ADMIN_EMAIL: str = "admin@nexvault.internal"
    INITIAL_ADMIN_PASSWORD: str = "AdminSecurePassword2026!"
    INITIAL_ADMIN_NAME: str = "NexVault System Administrator"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    # Storage Nodes
    STORAGE_NODE_HOST: str = "127.0.0.1"
    STORAGE_NODE_PORTS: str = "5001,5002,5003,5004,5005,5006"
    STORAGE_DIR_BASE: str = "./storage"

    # Self-Healing & Health Check intervals (seconds)
    HEALTH_CHECK_INTERVAL_SECONDS: float = 3.0
    REPAIR_WORKER_INTERVAL_SECONDS: float = 5.0
    INTEGRITY_SCAN_INTERVAL_SECONDS: float = 30.0
    REBALANCE_THRESHOLD_PERCENT: float = 20.0

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def node_ports(self) -> List[int]:
        return [int(p.strip()) for p in self.STORAGE_NODE_PORTS.split(",") if p.strip()]


settings = Settings()
