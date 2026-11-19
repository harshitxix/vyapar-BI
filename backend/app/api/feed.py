from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.schemas.article import ArticleResponse

router = APIRouter(prefix="/feed", tags=["Feed"])

DOMAIN_ALIASES = {
    "grocery": ["grocery", "fmcg"],
    "retail": ["retail"],
    "technology": ["technology", "electronics", "quick_commerce"],
    "fashion": ["fashion", "apparel"],
    "general_business": ["general_business", "manufacturing", "logistics"],
}


@router.get("", response_model=dict)
async def get_mobile_feed(
    domain: Optional[str] = Query(None, description="Domain filter: grocery, retail, fashion, technology, general_business"),
    region: Optional[str] = Query("india", description="Geographical region filter"),
    cursor: Optional[datetime] = Query(None, description="Cursor for pagination (published_at of last article)"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    High-performance, mobile-optimized article feed endpoint with cursor pagination and AI domain filtering.
    """
    query = (
        select(Article)
        .outerjoin(ArticleEnrichment, Article.id == ArticleEnrichment.article_id)
        .options(selectinload(Article.enrichment))
    )

    if domain and domain.lower() != "all":
        d_key = domain.lower()
        target_domains = DOMAIN_ALIASES.get(d_key, [d_key])
        query = query.where(
            or_(
                ArticleEnrichment.primary_domain.in_(target_domains),
                and_(
                    ArticleEnrichment.primary_domain.is_(None),
                    Article.business_domain.in_(target_domains),
                ),
            )
        )
    if region and region.lower() != "all":
        query = query.where(Article.region == region.lower())

    if cursor:
        query = query.where(Article.published_at < cursor)

    # Order by publication date desc, then insertion id
    query = query.order_by(desc(Article.published_at), desc(Article.created_at)).limit(limit + 1)

    result = await db.execute(query)
    articles = list(result.scalars().all())

    has_more = len(articles) > limit
    feed_items = articles[:limit]
    next_cursor = feed_items[-1].published_at.isoformat() if (feed_items and has_more) else None

    return {
        "status": "success",
        "count": len(feed_items),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "items": [ArticleResponse.model_validate(a) for a in feed_items]
    }
