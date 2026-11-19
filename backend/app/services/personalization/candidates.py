from datetime import datetime, timezone, timedelta
from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.models.trend import Trend
from backend.app.models.personalization import UserMarketProfile, CanonicalEntity
from backend.app.services.personalization.config import DEFAULT_PERSONALIZATION_CONFIG
from backend.app.services.personalization.taxonomy import TaxonomyService


@dataclass
class ArticleCandidate:
    article: Article
    enrichment: Optional[ArticleEnrichment]
    primary_domain: str
    secondary_domains: List[str]
    topics: List[str]
    entities: List[Dict[str, Any]]
    published_at: datetime
    region: str
    relevance_score: float


class CandidateGenerationService:
    """
    Retrieves a high-quality candidate subset of articles and trends from PostgreSQL
    using indexed filters, avoiding full-table scans.
    """

    @classmethod
    async def get_article_candidates(
        cls,
        db: AsyncSession,
        profile: Optional[UserMarketProfile],
        followed_topics: List[str],
        followed_entities: List[CanonicalEntity],
        window_days: int = 14,
        max_candidates: int = 150,
    ) -> List[ArticleCandidate]:
        """
        Retrieves up to max_candidates articles matching domain, followed topics,
        or followed entities within window_days.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
        user_domain = profile.business_domain if profile else "grocery"

        # Extract followed entity names and aliases
        entity_keywords = set()
        for ent in followed_entities:
            entity_keywords.add(ent.name.lower())
            if ent.aliases:
                for a in ent.aliases:
                    entity_keywords.add(a.lower())

        topic_set = set(t.lower() for t in followed_topics)

        # Build indexed query
        query = (
            select(Article)
            .options(selectinload(Article.enrichment))
            .where(
                Article.status == "published",
                Article.published_at >= cutoff_date,
            )
            .order_by(desc(Article.published_at))
            .limit(max_candidates * 2)  # Over-fetch slightly for high-relevance filtering
        )

        result = await db.execute(query)
        articles = result.scalars().all()

        candidates: List[ArticleCandidate] = []
        for art in articles:
            enr = art.enrichment
            prim_domain = (enr.primary_domain if enr else None) or art.business_domain or "general_business"
            sec_domains = (enr.secondary_domains if enr and enr.secondary_domains else [])
            topics = (enr.topics if enr and enr.topics else [])
            entities = (enr.entities if enr and enr.entities else [])
            rel_score = (enr.relevance_score if enr and enr.relevance_score is not None else 0.5)

            # Inclusion criteria:
            # 1. Matches primary domain or secondary domains or related domains
            # 2. General business macro updates
            # 3. Topic / Entity match with domain affinity
            related_domains = set(TaxonomyService.get_related_domains(user_domain))
            is_domain_match = (
                prim_domain == user_domain
                or user_domain in sec_domains
                or prim_domain == "general_business"
                or prim_domain in related_domains
            )
            is_topic_match = any(t.lower() in topic_set for t in topics)
            is_entity_match = False
            if entity_keywords and entities:
                for e in entities:
                    ename = (e.get("name") if isinstance(e, dict) else str(e)).lower()
                    if ename in entity_keywords:
                        is_entity_match = True
                        break

            # Include if matching user domain/related domains, or if explicitly matched topic/entity
            if is_domain_match or ((is_topic_match or is_entity_match) and (prim_domain in related_domains or prim_domain == "general_business")):
                candidates.append(
                    ArticleCandidate(
                        article=art,
                        enrichment=enr,
                        primary_domain=prim_domain,
                        secondary_domains=sec_domains,
                        topics=topics,
                        entities=entities,
                        published_at=art.published_at,
                        region=art.region or "india",
                        relevance_score=rel_score,
                    )
                )
                if len(candidates) >= max_candidates:
                    break

        # Fallback if sparse (e.g. fresh environment or niche profile):
        if len(candidates) < 10:
            for art in articles:
                if any(c.article.id == art.id for c in candidates):
                    continue
                enr = art.enrichment
                candidates.append(
                    ArticleCandidate(
                        article=art,
                        enrichment=enr,
                        primary_domain=(enr.primary_domain if enr else None) or art.business_domain,
                        secondary_domains=(enr.secondary_domains if enr and enr.secondary_domains else []),
                        topics=(enr.topics if enr and enr.topics else []),
                        entities=(enr.entities if enr and enr.entities else []),
                        published_at=art.published_at,
                        region=art.region or "india",
                        relevance_score=(enr.relevance_score if enr and enr.relevance_score is not None else 0.5),
                    )
                )
                if len(candidates) >= max_candidates:
                    break

        return candidates

    @classmethod
    async def get_trend_candidates(
        cls,
        db: AsyncSession,
        profile: Optional[UserMarketProfile],
        limit: int = 50,
    ) -> List[Trend]:
        """
        Retrieves active Phase 3 market trends for personalization.
        """
        query = (
            select(Trend)
            .where(Trend.status.in_(["emerging", "growing", "established"]))
            .order_by(desc(Trend.strength_score))
            .limit(limit)
        )
        res = await db.execute(query)
        trends = list(res.scalars().all())

        # If sparse, return all available trends
        if not trends:
            fallback_res = await db.execute(
                select(Trend).order_by(desc(Trend.strength_score)).limit(limit)
            )
            trends = list(fallback_res.scalars().all())

        return trends
