from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging, logger
from app.core.init_db import init_db
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.api.v1.health import router as health_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # Initialize DB tables and baseline seeds
    await init_db()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NEXVAULT Fault-Tolerant Distributed Object Storage Control Plane",
    lifespan=lifespan,
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Include Routers
app.include_router(health_router)
app.include_router(api_v1_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "tagline": "Storage that survives failure.",
        "version": settings.APP_VERSION,
        "status": "ONLINE",
        "docs_url": "/docs",
    }
