import asyncio
from typing import Dict, Any, Optional
from app.core.database import get_session_factory
from app.core.config import settings
from app.core.logging_config import logger
from app.services.repair_service import RepairService


class RepairWorker:
    """Asynchronous background worker discovering and repairing degraded replicas across the cluster."""

    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Background RepairWorker started with interval {settings.REPAIR_WORKER_INTERVAL_SECONDS}s")

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Background RepairWorker stopped")

    async def reconcile_once(self) -> Dict[str, Any]:
        """Performs a single synchronous reconciliation cycle across the cluster."""
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = RepairService(session)
            result = await service.run_cluster_reconciliation()
            await session.commit()
            return result

    async def _run_loop(self):
        # Initial small delay to let server initialize completely
        await asyncio.sleep(2.0)
        while self.running:
            try:
                res = await self.reconcile_once()
                if res.get("repairs_executed", 0) > 0:
                    logger.info(f"RepairWorker reconciled {res['repairs_executed']} degraded object(s)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in RepairWorker cycle: {e}")

            try:
                await asyncio.sleep(settings.REPAIR_WORKER_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break


repair_worker = RepairWorker()
