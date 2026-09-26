"""
NEXVAULT Control Plane Coordinator
FastAPI application orchestrating distributed metadata, durability policies,
background self-healing, real-time observability, and Chaos Lab.
"""

import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.init_db import init_database
from backend.app.services.heartbeat import probe_and_update_cluster
from backend.app.services.repair_engine import run_repair_cycle

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.buckets import router as buckets_router
from backend.app.api.v1.objects import router as objects_router
from backend.app.api.v1.cluster import router as cluster_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.chaos import router as chaos_router

_background_tasks = set()


async def background_heartbeat_worker():
    """
    Continuous probe loop.
    Pings all 6 nodes every 3 seconds, updates status, and triggers self-repair on degradation.
    """
    await asyncio.sleep(2.0)  # Wait for startup
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await probe_and_update_cluster(session)
                # Auto-heal any under-replicated objects
                await run_repair_cycle(session)
        except Exception as e:
            # Don't let worker crash on transient db errors
            pass
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables & seed data exist
    await init_database()

    # Start background heartbeat & repair loop
    task = asyncio.create_task(background_heartbeat_worker())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=f"{settings.TAGLINE} - Fault-tolerant distributed object storage coordinator.",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(buckets_router, prefix=api_prefix)
app.include_router(objects_router, prefix=api_prefix)
app.include_router(cluster_router, prefix=api_prefix)
app.include_router(events_router, prefix=api_prefix)
app.include_router(chaos_router, prefix=api_prefix)


@app.get("/")
async def root():
    return {
        "product": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "status": "OPERATIONAL",
        "documentation": "/docs",
    }
