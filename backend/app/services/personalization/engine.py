import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.personalization import UserMarketProfile, CanonicalEntity
from backend.app.services.personalization.config import (
    PersonalizationConfig,
    DEFAULT_PERSONALIZATION_CONFIG,
)
from backend.app.services.personalization.user_service import UserProfileService
from backend.app.services.personalization.entity_service import EntityFollowService
from backend.app.services.personalization.candidates import CandidateGenerationService
from backend.app.services.personalization.scoring import (
    ArticleRelevanceService,
    TrendRelevanceService,
    ScoredArticle,
    ScoredTrend,
)
from backend.app.services.personalization.diversity import DiversityService
from backend.app.services.personalization.feedback import FeedbackService

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    """
    Main orchestration engine generating personalized, diversified market feeds.
    """

    def __init__(self, config: PersonalizationConfig = DEFAULT_PERSONALIZATION_CONFIG):
        self.config = config

    async def generate_for_you_feed(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates the primary personalized feed combining articles and relevant market trends.
        """
        start_time = time.perf_counter()

        # 1. Fetch user context
        profile = await UserProfileService.get_profile(db, user_id)
        interests = await UserProfileService.get_interests(db, user_id)
        user_topics = {i.topic_id: i.preference_score for i in interests}

        followed_entities = await EntityFollowService.get_user_followed_entities(db, user_id)
        user_settings = await UserProfileService.get_feed_preferences(db, user_id)
        learned_prefs = await FeedbackService.get_learned_preference_dict(db, user_id, self.config)

        # 2. Candidate Generation
        active_trends = await CandidateGenerationService.get_trend_candidates(
            db, profile, limit=self.config.candidate_max_trends
        )
        article_candidates = await CandidateGenerationService.get_article_candidates(
            db,
            profile=profile,
            followed_topics=list(user_topics.keys()),
            followed_entities=followed_entities,
            window_days=self.config.candidate_window_days,
            max_candidates=self.config.candidate_max_articles,
        )

        # 3. Scoring
        scored_articles: List[ScoredArticle] = [
            ArticleRelevanceService.score_candidate(
                candidate=cand,
                profile=profile,
                user_topics=user_topics,
                followed_entities=followed_entities,
                learned_prefs=learned_prefs,
                user_settings=user_settings,
                active_trends=active_trends,
                config=self.config,
            )
            for cand in article_candidates
        ]

        scored_trends: List[ScoredTrend] = [
            TrendRelevanceService.score_trend(
                trend=tr,
                profile=profile,
                user_topics=user_topics,
                followed_entities=followed_entities,
                config=self.config,
            )
            for tr in active_trends
        ]

        # 4. Diversity Re-Ranking
        diversified_articles = DiversityService.apply_diversity_reranking(
            scored_articles, config=self.config
        )
        ranked_trends = sorted(scored_trends, key=lambda t: t.final_score, reverse=True)

        # 5. Composite Feed Blending (1 trend for every 4-5 articles)
        feed_items: List[Dict[str, Any]] = []
        trend_idx = 0

        for i, sc_art in enumerate(diversified_articles):
            # Inject top trend periodically if available and relevant to user domain
            if i > 0 and i % 4 == 0 and trend_idx < len(ranked_trends):
                t_item = ranked_trends[trend_idx]
                trend_idx += 1
                if t_item.user_relevance_score >= 0.25:
                    feed_items.append({
                        "type": "trend",
                        "id": t_item.trend.id,
                        "title": t_item.trend.name,
                        "description": t_item.trend.description,
                        "domain": t_item.trend.domain,
                        "region": t_item.trend.region,
                        "category": t_item.trend.category,
                        "status": t_item.trend.status,
                        "strength_score": t_item.market_strength_score,
                        "user_relevance_score": t_item.user_relevance_score,
                        "final_score": t_item.final_score,
                        "article_count": t_item.trend.article_count,
                        "source_count": t_item.trend.source_count,
                        "personalization": {
                            "reasons": t_item.reasons,
                            "matched_topics": t_item.matched_topics,
                            "matched_entities": t_item.matched_entities,
                        },
                    })

            art = sc_art.candidate.article
            enr = sc_art.candidate.enrichment
            feed_items.append({
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
                "published_at": art.published_at.isoformat(),
                "business_domain": sc_art.candidate.primary_domain or art.business_domain,
                "category": art.category or (enr.category if enr else None),
                "subcategory": art.subcategory,
                "region": art.region or "india",
                "author": art.author,
                "relevance_score": sc_art.final_score,
                "enrichment": {
                    "summary": enr.summary if enr else None,
                    "topics": sc_art.candidate.topics,
                    "entities": sc_art.candidate.entities,
                    "relevance_score": sc_art.candidate.relevance_score,
                } if enr else None,
                "personalization": {
                    "reasons": sc_art.reasons,
                    "matched_topics": sc_art.matched_topics,
                    "matched_entities": sc_art.matched_entities,
                    "signals": sc_art.raw_signals,
                },
            })

        # Apply Cursor Pagination
        offset = 0
        if cursor and cursor.isdigit():
            offset = int(cursor)

        paginated_items = feed_items[offset : offset + limit]
        next_cursor = str(offset + limit) if (offset + limit) < len(feed_items) else None

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "status": "success",
            "count": len(paginated_items),
            "total_candidates": len(article_candidates),
            "has_more": next_cursor is not None,
            "next_cursor": next_cursor,
            "items": paginated_items,
            "diagnostics": {
                "latency_ms": latency_ms,
                "articles_scored": len(scored_articles),
                "trends_scored": len(scored_trends),
                "user_domain": profile.business_domain if profile else "default",
                "config_version": self.config.config_version,
            },
        }

    async def generate_following_feed(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Feed showing updates specifically connected to user's followed topics and entities.
        """
        for_you = await self.generate_for_you_feed(db, user_id, limit=limit * 2)
        following_items = [
            item
            for item in for_you["items"]
            if item.get("personalization", {}).get("matched_topics")
            or item.get("personalization", {}).get("matched_entities")
        ]

        offset = 0
        if cursor and cursor.isdigit():
            offset = int(cursor)

        sliced = following_items[offset : offset + limit]
        next_cursor = str(offset + limit) if (offset + limit) < len(following_items) else None

        return {
            "status": "success",
            "count": len(sliced),
            "has_more": next_cursor is not None,
            "next_cursor": next_cursor,
            "items": sliced,
        }

    async def generate_personalized_trends(
        self, db: AsyncSession, user_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Ranks active trends according to user relevance.
        """
        profile = await UserProfileService.get_profile(db, user_id)
        interests = await UserProfileService.get_interests(db, user_id)
        user_topics = {i.topic_id: i.preference_score for i in interests}
        followed_entities = await EntityFollowService.get_user_followed_entities(db, user_id)

        trends = await CandidateGenerationService.get_trend_candidates(db, profile, limit=limit * 2)
        scored: List[ScoredTrend] = [
            TrendRelevanceService.score_trend(
                trend=tr,
                profile=profile,
                user_topics=user_topics,
                followed_entities=followed_entities,
                config=self.config,
            )
            for tr in trends
        ]

        scored.sort(key=lambda t: t.final_score, reverse=True)

        return [
            {
                "id": t.trend.id,
                "name": t.trend.name,
                "description": t.trend.description,
                "domain": t.trend.domain,
                "region": t.trend.region,
                "category": t.trend.category,
                "status": t.trend.status,
                "evidence_grade": t.trend.evidence_grade,
                "strength_score": t.market_strength_score,
                "user_relevance_score": t.user_relevance_score,
                "final_score": t.final_score,
                "article_count": t.trend.article_count,
                "source_count": t.trend.source_count,
                "representative_topics": t.trend.representative_topics,
                "representative_entities": t.trend.representative_entities,
                "personalization": {
                    "reasons": t.reasons,
                    "matched_topics": t.matched_topics,
                    "matched_entities": t.matched_entities,
                },
            }
            for t in scored[:limit]
        ]


personalization_engine = PersonalizationEngine()
