import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.app.database.session import get_db, AsyncSessionLocal
from backend.app.models.ingestion_run import IngestionRun
from backend.app.schemas.ingestion import IngestionTriggerRequest, IngestionRunResponse
from backend.app.services.ingestion.pipeline import IngestionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingestion", tags=["Ingestion"])
service = IngestionService()


async def _run_background_ingestion(source_id: Optional[str] = None, domain: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        try:
            logger.info(f"[API] Starting background ingestion run (source_id={source_id}, domain={domain})...")
            await service.run_pipeline(session, trigger_type="manual", source_id=source_id, domain_filter=domain)
            logger.info("[API] Background ingestion run finished.")
        except Exception as e:
            logger.error(f"[API] Error in background ingestion run: {e}")


@router.post("/refresh", status_code=202)
async def trigger_refresh(
    payload: Optional[IngestionTriggerRequest] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers an asynchronous manual ingestion run without blocking the client.
    """
    source_id = payload.source_id if payload else None
    domain = payload.domain if payload else None

    # Schedule background ingestion
    background_tasks.add_task(_run_background_ingestion, source_id=source_id, domain=domain)

    return {
        "status": "accepted",
        "message": "Manual ingestion cycle initiated in background.",
        "target_source": source_id or "all_active",
        "domain_filter": domain or "all"
    }


@router.get("/status", response_model=List[IngestionRunResponse])
async def list_recent_runs(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    query = select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()
    return runs


@router.get("/runs/{run_id}", response_model=IngestionRunResponse)
async def get_run_details(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Ingestion run '{run_id}' not found.")
    return run
