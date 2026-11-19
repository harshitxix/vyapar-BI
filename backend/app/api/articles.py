from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_, func
from sqlalchemy.orm import selectinload

from backend.app.database.session import get_db
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.schemas.article import ArticleResponse

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=dict)
async def list_articles(
    business_domain: Optional[str] = Query(None, description="Filter by business domain (e.g. grocery, retail, fashion, technology)"),
    region: Optional[str] = Query(None, description="Filter by region (e.g. india)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    search: Optional[str] = Query(None, description="Keyword search in title or description"),
    from_date: Optional[datetime] = Query(None, description="Filter published after this UTC timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter published before this UTC timestamp"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Article)
        .outerjoin(ArticleEnrichment, Article.id == ArticleEnrichment.article_id)
        .options(selectinload(Article.enrichment))
    )
    count_query = select(func.count(Article.id)).outerjoin(
        ArticleEnrichment, Article.id == ArticleEnrichment.article_id
    )

    filters = []
    if business_domain:
        d_key = business_domain.lower()
        filters.append(
            or_(
                ArticleEnrichment.primary_domain == d_key,
                and_(
                    ArticleEnrichment.primary_domain.is_(None),
                    Article.business_domain == d_key,
                ),
            )
        )
    if region:
        filters.append(Article.region == region.lower())
    if category:
        filters.append(Article.category == category)
    if source_id:
        filters.append(Article.source_id == source_id)
    if from_date:
        filters.append(Article.published_at >= from_date)
    if to_date:
        filters.append(Article.published_at <= to_date)
    if search:
        search_pattern = f"%{search.strip()}%"
        filters.append(or_(Article.title.ilike(search_pattern), Article.description.ilike(search_pattern)))

    if filters:
        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

    # Order by publication date descending
    query = query.order_by(desc(Article.published_at)).offset(offset).limit(limit)

    total_res = await db.execute(count_query)
    total_count = total_res.scalar() or 0

    articles_res = await db.execute(query)
    articles = articles_res.scalars().all()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "items": [ArticleResponse.model_validate(a) for a in articles]
    }


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_detail(article_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.enrichment)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found.")
    return ArticleResponse.model_validate(article)
