import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from backend.app.database.session import get_db, AsyncSessionLocal
from backend.app.models.trend import Trend, TrendArticle, TrendSnapshot, TrendAnalysisRun
from backend.app.schemas.trend import (
    TrendSummaryResponse,
    TrendDetailResponse,
    SupportingArticleItem,
    TrendSnapshotResponse,
    TrendAnalysisRunResponse,
    TrendRebuildRequest,
)
from backend.app.services.trends.engine import TrendEngine

logger = logging.getLogger("vyapar.api.trends")
router = APIRouter(prefix="/trends", tags=["Market Trends"])


@router.get("", response_model=List[TrendSummaryResponse])
async def list_trends(
    domain: Optional[str] = Query(None, description="Filter by market domain e.g. grocery, retail, tech"),
    region: Optional[str] = Query(None, description="Filter by region e.g. india"),
    category: Optional[str] = Query(None, description="Filter by category e.g. Consumer Trend"),
    status: Optional[str] = Query(None, description="Filter by status: emerging, growing, established, cooling, declining"),
    min_strength: float = Query(0.0, ge=0.0, le=1.0, description="Minimum strength score"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List detected market trends sorted by strength and recency.
    """
    conditions = [Trend.status != "inactive", Trend.strength_score >= min_strength]

    if domain and domain.lower() != "all":
        conditions.append(Trend.domain.ilike(f"%{domain}%"))

    if region and region.lower() != "all":
        conditions.append(Trend.region.ilike(f"%{region}%"))

    if category and category.lower() != "all":
        conditions.append(Trend.category.ilike(f"%{category}%"))

    if status and status.lower() != "all":
        conditions.append(Trend.status == status.lower())

    stmt = (
        select(Trend)
        .where(and_(*conditions))
        .order_by(desc(Trend.strength_score), desc(Trend.last_updated_at))
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    trends = result.scalars().all()

    return [
        TrendSummaryResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            domain=t.domain,
            region=t.region,
            category=t.category,
            status=t.status,
            evidence_grade=t.evidence_grade,
            strength_score=t.strength_score,
            confidence_score=t.confidence_score,
            momentum_score=t.momentum_score,
            article_count=t.article_count,
            source_count=t.source_count,
            first_detected_at=t.first_detected_at,
            last_updated_at=t.last_updated_at,
            representative_topics=t.representative_topics or [],
        )
        for t in trends
    ]


@router.get("/emerging", response_model=List[TrendSummaryResponse])
async def list_emerging_trends(
    domain: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top newly emerging market trends.
    """
    return await list_trends(domain=domain, status="emerging", limit=limit, offset=0, db=db)


@router.get("/growing", response_model=List[TrendSummaryResponse])
async def list_growing_trends(
    domain: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top accelerating / growing market trends.
    """
    return await list_trends(domain=domain, status="growing", limit=limit, offset=0, db=db)


@router.get("/{trend_id}", response_model=TrendDetailResponse)
async def get_trend_detail(
    trend_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive trend detail with detection rationale, key developments, and supporting stories.
    """
    stmt = (
        select(Trend)
        .options(
            selectinload(Trend.trend_articles).selectinload(TrendArticle.article)
        )
        .where(Trend.id == trend_id)
    )
    res = await db.execute(stmt)
    trend = res.scalar_one_or_none()

    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")

    supporting_items = []
    if trend.trend_articles:
        for ta in trend.trend_articles:
            if ta.article:
                supporting_items.append(
                    SupportingArticleItem(
                        id=ta.article.id,
                        title=ta.article.title,
                        source_name=ta.article.source_name,
                        published_at=ta.article.published_at,
                        original_url=ta.article.original_url,
                        image_url=ta.article.image_url,
                        similarity_score=ta.similarity_score,
                    )
                )

    return TrendDetailResponse(
        id=trend.id,
        name=trend.name,
        description=trend.description,
        why_emerging=trend.why_emerging,
        key_developments=trend.key_developments or [],
        domain=trend.domain,
        region=trend.region,
        category=trend.category,
        status=trend.status,
        evidence_grade=trend.evidence_grade,
        strength_score=trend.strength_score,
        confidence_score=trend.confidence_score,
        momentum_score=trend.momentum_score,
        coherence_score=trend.coherence_score,
        diversity_score=trend.diversity_score,
        article_count=trend.article_count,
        source_count=trend.source_count,
        representative_topics=trend.representative_topics or [],
        representative_entities=[
            e if isinstance(e, str) else e.get("name", str(e))
            for e in (trend.representative_entities or [])
        ],
        first_detected_at=trend.first_detected_at,
        last_updated_at=trend.last_updated_at,
        supporting_articles=supporting_items,
    )


@router.get("/{trend_id}/timeline", response_model=List[TrendSnapshotResponse])
async def get_trend_timeline(
    trend_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get chronological snapshots showing how the trend evolved over time.
    """
    stmt = (
        select(TrendSnapshot)
        .where(TrendSnapshot.trend_id == trend_id)
        .order_by(TrendSnapshot.timestamp.asc())
    )
    res = await db.execute(stmt)
    snapshots = res.scalars().all()
    return snapshots


# Admin operations
admin_router = APIRouter(prefix="/admin/trends", tags=["Trend Admin"])


async def _run_trend_rebuild_task(domain: Optional[str], region: str, window_days: int, baseline_days: int):
    async with AsyncSessionLocal() as session:
        engine = TrendEngine()
        await engine.run_trend_detection(
            db=session,
            domain=domain,
            region=region,
            window_days=window_days,
            baseline_days=baseline_days,
        )


@admin_router.post("/rebuild")
async def trigger_trend_rebuild(
    request: TrendRebuildRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an asynchronous trend detection run.
    """
    background_tasks.add_task(
        _run_trend_rebuild_task,
        request.domain,
        request.region,
        request.window_days,
        request.baseline_days,
    )
    return {"message": "Trend detection run initiated in background", "params": request.model_dump()}


@admin_router.get("/runs", response_model=List[TrendAnalysisRunResponse])
async def get_trend_runs(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get history of trend detection runs.
    """
    stmt = select(TrendAnalysisRun).order_by(desc(TrendAnalysisRun.started_at)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
