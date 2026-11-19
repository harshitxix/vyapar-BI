from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from backend.app.database.session import get_db
from backend.app.models.personalization import User
from backend.app.models.article import Article
from backend.app.api.auth import get_current_user
from backend.app.schemas.personalization import PersonalizedFeedResponse
from backend.app.services.personalization.engine import personalization_engine

router = APIRouter(prefix="", tags=["Personalized Feeds"])


@router.get("/feed/for-you", response_model=PersonalizedFeedResponse)
async def get_for_you_feed(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main personalized feed blending articles and market trends based on user domain,
    location, followed topics, entities, and past interactions.
    """
    res = await personalization_engine.generate_for_you_feed(
        db=db,
        user_id=current_user.id,
        limit=limit,
        cursor=cursor,
    )
    return res


@router.get("/feed/following", response_model=PersonalizedFeedResponse)
async def get_following_feed(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Feed filtered strictly to articles and updates matching the user's
    explicitly followed topics and entities.
    """
    res = await personalization_engine.generate_following_feed(
        db=db,
        user_id=current_user.id,
        limit=limit,
        cursor=cursor,
    )
    return res


@router.get("/trends/for-you")
async def get_personalized_trends(
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Active market trends ranked according to user business domain,
    geographic location, followed topics, and entities.
    """
    trends = await personalization_engine.generate_personalized_trends(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )
    return {"status": "success", "count": len(trends), "items": trends}


@router.get("/feed/latest", response_model=PersonalizedFeedResponse)
async def get_latest_feed(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Unpersonalized baseline feed showing latest articles in pure reverse-chronological order.
    Useful for comparison, fallback, and initial discovery.
    """
    offset = 0
    if cursor and cursor.isdigit():
        offset = int(cursor)

    stmt = (
        select(Article)
        .options(selectinload(Article.enrichment))
        .order_by(desc(Article.published_at))
        .offset(offset)
        .limit(limit + 1)
    )
    res = await db.execute(stmt)
    articles = list(res.scalars().all())

    has_more = len(articles) > limit
    returned_articles = articles[:limit]
    next_cursor = str(offset + limit) if has_more else None

    items = []
    for art in returned_articles:
        enr = art.enrichment
        items.append({
            "type": "article",
            "id": art.id,
            "title": art.title,
            "description": art.description,
            "source_id": art.source_id,
            "source_name": art.source_name,
            "source_domain": art.source_domain,
            "original_url": art.original_url,
            "canonical_url": art.canonical_url,
            "image_url": art.image_url,
            "published_at": art.published_at.isoformat() if art.published_at else "",
            "business_domain": (enr.primary_domain if (enr and enr.primary_domain) else art.business_domain),
            "category": art.category,
            "subcategory": art.subcategory,
            "relevance_score": 0.5,
            "enrichment": {
                "summary": enr.summary if enr else None,
                "topics": enr.topics if enr else [],
                "entities": enr.entities if enr else [],
                "relevance_score": enr.relevance_score if enr else None,
            } if enr else None,
            "personalization": {
                "reasons": ["Chronological order: Most recent publication"],
                "matched_topics": [],
                "matched_entities": [],
                "signals": {},
            },
        })

    return {
        "status": "success",
        "count": len(items),
        "total_candidates": len(items),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "items": items,
        "diagnostics": {
            "mode": "chronological",
        },
    }
