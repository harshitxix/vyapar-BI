import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db, AsyncSessionLocal
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.schemas.enrichment import ArticleEnrichmentRead
from backend.app.services.ai.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ai", tags=["AI Enrichment Admin"])
enrichment_service = EnrichmentService()


@router.post("/reprocess/{article_id}", response_model=ArticleEnrichmentRead)
async def reprocess_article(
    article_id: str,
    force: bool = Query(True, description="Force re-enrichment even if already completed"),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually reprocess / enrich a specific article with the AI pipeline.
    """
    record = await enrichment_service.enrich_article(article_id=article_id, db=db, force=force)
    if not record:
        raise HTTPException(status_code=404, detail="Article not found")
    return record


async def _run_batch_enrichment_task(batch_size: int):
    async with AsyncSessionLocal() as session:
        try:
            await enrichment_service.enrich_pending_articles(db=session, batch_size=batch_size)
        except Exception as e:
            logger.exception(f"Background batch enrichment failed: {e}")


@router.post("/reprocess-batch")
async def reprocess_batch(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(10, ge=1, le=50, description="Number of pending articles to enrich"),
):
    """
    Trigger an asynchronous batch enrichment for pending/failed articles.
    """
    background_tasks.add_task(_run_batch_enrichment_task, batch_size)
    return {
        "status": "queued",
        "message": f"Queued background AI enrichment batch for up to {batch_size} articles."
    }


@router.get("/status")
async def get_enrichment_status(db: AsyncSession = Depends(get_db)):
    """
    Observability metrics on AI enrichment: total articles, completed, pending, failed, token usage.
    """
    # Total articles
    total_articles = await db.scalar(select(func.count(Article.id))) or 0

    # Counts by status
    status_counts_res = await db.execute(
        select(ArticleEnrichment.status, func.count(ArticleEnrichment.id)).group_by(ArticleEnrichment.status)
    )
    status_map = dict(status_counts_res.all())

    # Aggregates
    agg_res = await db.execute(
        select(
            func.sum(ArticleEnrichment.input_tokens),
            func.sum(ArticleEnrichment.output_tokens),
            func.avg(ArticleEnrichment.latency_ms),
            func.avg(ArticleEnrichment.relevance_score),
        ).where(ArticleEnrichment.status == "completed")
    )
    tot_input, tot_output, avg_lat, avg_rel = agg_res.one()

    return {
        "total_articles": total_articles,
        "enrichment_status_breakdown": {
            "completed": status_map.get("completed", 0),
            "pending": status_map.get("pending", 0),
            "failed": status_map.get("failed", 0),
            "processing": status_map.get("processing", 0),
            "not_queued": max(0, total_articles - sum(status_map.values())),
        },
        "metrics": {
            "total_input_tokens": tot_input or 0,
            "total_output_tokens": tot_output or 0,
            "average_latency_ms": round(avg_lat or 0, 1),
            "average_relevance_score": round(avg_rel or 0.0, 3),
        },
        "model_configured": enrichment_service.provider.model_name,
    }
