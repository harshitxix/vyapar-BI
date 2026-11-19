from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.app.database.session import get_db
from backend.app.models.source import Source
from backend.app.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from backend.app.scheduler.manager import scheduler_manager

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get("", response_model=List[SourceResponse])
async def list_sources(
    active: Optional[bool] = None,
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Source)
    if active is not None:
        query = query.where(Source.active == active)
    
    result = await db.execute(query)
    sources = result.scalars().all()

    if domain:
        sources = [s for s in sources if s.business_domains and domain in s.business_domains]

    return sources


@router.get("/status")
async def get_sources_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source))
    sources = result.scalars().all()

    healthy_count = sum(1 for s in sources if s.status == "healthy")
    degraded_count = sum(1 for s in sources if s.status == "degraded")
    failed_count = sum(1 for s in sources if s.status == "failed")
    total = len(sources)

    return {
        "total_sources": total,
        "healthy": healthy_count,
        "degraded": degraded_count,
        "failed": failed_count,
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "domain": s.domain,
                "status": s.status,
                "failure_count": s.failure_count,
                "last_checked": s.last_checked,
                "last_success": s.last_success,
                "last_failure": s.last_failure,
                "last_response_time_ms": s.last_response_time_ms,
                "last_article_count": s.last_article_count
            }
            for s in sources
        ]
    }


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
    return source


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Source).where(Source.id == payload.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Source with id '{payload.id}' already exists.")

    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Sync scheduler
    await scheduler_manager.sync_source_jobs()
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: str, payload: SourceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(source, k, v)

    await db.commit()
    await db.refresh(source)

    # Sync scheduler
    await scheduler_manager.sync_source_jobs()
    return source
