import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from backend.app.database.session import AsyncSessionLocal
from backend.app.models.source import Source
from backend.app.services.ingestion.pipeline import IngestionService
from backend.app.services.ai.enrichment_service import EnrichmentService
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)


class SchedulerManager:
    """
    Manages background scheduled polling of registered sources using APScheduler.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.service = IngestionService()
        self.enrichment_service = EnrichmentService()
        self._is_running = False

    async def _poll_source_job(self, source_id: str):
        """Worker job to ingest a single due source."""
        logger.info(f"[SCHEDULER] Triggering scheduled poll for source: {source_id}")
        async with AsyncSessionLocal() as session:
            try:
                res = await session.execute(select(Source).where(Source.id == source_id, Source.active == True))
                source = res.scalar_one_or_none()
                if not source:
                    logger.warning(f"[SCHEDULER] Source {source_id} not found or inactive, skipping.")
                    return

                await self.service.ingest_source(session, source)
            except Exception as e:
                logger.error(f"[SCHEDULER] Error during scheduled poll for {source_id}: {e}")

    async def _enrichment_worker_job(self):
        """Worker job to enrich newly ingested pending articles."""
        if not settings.AI_ENRICHMENT_ENABLED:
            return

        async with AsyncSessionLocal() as session:
            try:
                enriched = await self.enrichment_service.enrich_pending_articles(
                    session, batch_size=settings.AI_BATCH_SIZE
                )
                if enriched:
                    logger.info(f"[SCHEDULER-AI] Enriched {len(enriched)} pending articles.")
            except Exception as e:
                logger.error(f"[SCHEDULER-AI] Error during background enrichment worker: {e}")

    async def sync_source_jobs(self):
        """Reads active sources from DB and registers interval jobs in scheduler."""
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Source).where(Source.active == True))
            sources = res.scalars().all()

            for source in sources:
                job_id = f"poll_source_{source.id}"
                interval_seconds = max(60, source.refresh_interval or settings.DEFAULT_POLL_INTERVAL)

                # Add or update job
                self.scheduler.add_job(
                    self._poll_source_job,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    args=[source.id],
                    id=job_id,
                    replace_existing=True,
                    name=f"Poll {source.name}"
                )
                logger.info(f"[SCHEDULER] Registered job '{job_id}' every {interval_seconds}s")

    async def _trend_detection_worker_job(self):
        """Worker job to periodically run trend detection analysis."""
        from backend.app.services.trends.engine import TrendEngine
        async with AsyncSessionLocal() as session:
            try:
                engine = TrendEngine()
                await engine.run_trend_detection(session, domain=None, region="india", window_days=14)
            except Exception as e:
                logger.error(f"[SCHEDULER-TRENDS] Error during background trend detection worker: {e}")

    async def start(self):
        if not settings.SCHEDULER_ENABLED:
            logger.info("[SCHEDULER] Scheduler is disabled via config.")
            return

        if not self._is_running:
            await self.sync_source_jobs()
            # Also schedule a periodic check every 5 minutes to refresh source schedule if sources change
            self.scheduler.add_job(
                self.sync_source_jobs,
                trigger=IntervalTrigger(minutes=5),
                id="sync_sources_job",
                replace_existing=True,
                name="Sync Source Registry"
            )

            # Schedule periodic background AI enrichment worker (every 30 seconds)
            if settings.AI_ENRICHMENT_ENABLED:
                self.scheduler.add_job(
                    self._enrichment_worker_job,
                    trigger=IntervalTrigger(seconds=30),
                    id="ai_enrichment_worker_job",
                    replace_existing=True,
                    name="AI Background Enrichment Worker"
                )
                logger.info("[SCHEDULER] Scheduled AI background enrichment worker every 30s.")

            # Schedule periodic background Trend Engine worker (every 30 minutes)
            self.scheduler.add_job(
                self._trend_detection_worker_job,
                trigger=IntervalTrigger(minutes=30),
                id="trend_detection_worker_job",
                replace_existing=True,
                name="Trend Engine Periodic Detection"
            )
            logger.info("[SCHEDULER] Scheduled Trend Engine detection worker every 30m.")

            self.scheduler.start()
            self._is_running = True
            logger.info("[SCHEDULER] APScheduler started successfully.")

    def shutdown(self):
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("[SCHEDULER] APScheduler stopped.")


scheduler_manager = SchedulerManager()
