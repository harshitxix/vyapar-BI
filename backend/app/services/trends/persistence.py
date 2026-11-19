import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from backend.app.models.trend import Trend, TrendArticle, TrendSnapshot
from backend.app.services.trends.clustering import ArticleCluster
from backend.app.services.trends.temporal import TemporalMetrics
from backend.app.services.trends.scoring import TrendScores
from backend.app.services.trends.synthesis import TrendSynthesisOutput
from backend.app.services.trends.similarity import SimilarityService

logger = logging.getLogger("vyapar.trends.persistence")


class TrendPersistenceService:
    """
    Manages matching candidate clusters to existing active trends,
    persisting new trends, updating evolving trends, and creating historical snapshots.
    """

    @staticmethod
    def _calculate_topic_overlap(topics1: List[str], topics2: List[str]) -> float:
        s1 = set(t.lower() for t in topics1 if t)
        s2 = set(t.lower() for t in topics2 if t)
        if not s1 or not s2:
            return 0.0
        intersection = len(s1.intersection(s2))
        union = len(s1.union(s2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    async def match_or_create_trend(
        cls,
        db: AsyncSession,
        cluster: ArticleCluster,
        temporal: TemporalMetrics,
        scores: TrendScores,
        synthesis: TrendSynthesisOutput,
        status: str,
        domain: str = "retail",
        region: str = "india",
        match_threshold: float = 0.55,
    ) -> Tuple[Trend, bool]:
        """
        Matches cluster against existing active trends.
        Returns (trend, is_new).
        """
        now = datetime.now(timezone.utc)
        
        # Query active trends in the same domain and region
        stmt = (
            select(Trend)
            .options(
                selectinload(Trend.trend_articles),
            )
            .where(
                and_(
                    Trend.domain == domain,
                    Trend.region == region,
                    Trend.status != "inactive",
                )
            )
        )
        res = await db.execute(stmt)
        existing_trends = res.scalars().all()

        best_match: Optional[Trend] = None
        best_score = 0.0

        cluster_topics = cluster.extract_top_topics(8)

        for ex_trend in existing_trends:
            # 1. Topic Jaccard overlap
            topic_sim = cls._calculate_topic_overlap(cluster_topics, ex_trend.representative_topics or [])
            
            # Combine signals
            combined_match = topic_sim
            if combined_match > best_score:
                best_score = combined_match
                best_match = ex_trend

        is_new = False
        if best_match and best_score >= match_threshold:
            # Update existing trend
            trend = best_match
            trend.name = synthesis.trend_name or trend.name
            trend.description = synthesis.trend_description or trend.description
            trend.why_emerging = synthesis.why_emerging or trend.why_emerging
            trend.key_developments = synthesis.key_developments or trend.key_developments
            trend.category = synthesis.category or trend.category
            trend.status = status
            trend.evidence_grade = scores.evidence_grade
            trend.strength_score = scores.strength_score
            trend.confidence_score = scores.confidence_score
            trend.momentum_score = scores.momentum_score
            trend.coherence_score = scores.coherence_score
            trend.diversity_score = scores.diversity_score
            trend.article_count = cluster.article_count
            trend.source_count = cluster.unique_source_count
            trend.representative_topics = cluster_topics
            trend.representative_entities = cluster.extract_top_entities(8)
            trend.last_updated_at = now
            trend.updated_at = now
        else:
            # Create new trend
            is_new = True
            trend = Trend(
                id=str(uuid.uuid4()),
                name=synthesis.trend_name,
                description=synthesis.trend_description,
                why_emerging=synthesis.why_emerging,
                key_developments=synthesis.key_developments,
                domain=domain,
                region=region,
                category=synthesis.category,
                status=status,
                evidence_grade=scores.evidence_grade,
                strength_score=scores.strength_score,
                confidence_score=scores.confidence_score,
                momentum_score=scores.momentum_score,
                coherence_score=scores.coherence_score,
                diversity_score=scores.diversity_score,
                article_count=cluster.article_count,
                source_count=cluster.unique_source_count,
                representative_topics=cluster_topics,
                representative_entities=cluster.extract_top_entities(8),
                first_detected_at=temporal.first_seen_at or now,
                last_updated_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(trend)
            await db.flush()

        # Update supporting articles
        if is_new:
            existing_art_ids = set()
        else:
            stmt_art = select(TrendArticle.article_id).where(TrendArticle.trend_id == trend.id)
            res_art = await db.execute(stmt_art)
            existing_art_ids = set(res_art.scalars().all())
        
        for cand in cluster.articles:
            if cand.id not in existing_art_ids:
                sim_score = 1.0
                if cluster.centroid and cand.embedding:
                    sim_score = SimilarityService.compute_cosine_similarity(cluster.centroid, cand.embedding)

                trend_art = TrendArticle(
                    id=str(uuid.uuid4()),
                    trend_id=trend.id,
                    article_id=cand.id,
                    similarity_score=round(sim_score, 3),
                    added_at=now,
                )
                db.add(trend_art)

        # Create historical snapshot
        snapshot = TrendSnapshot(
            id=str(uuid.uuid4()),
            trend_id=trend.id,
            timestamp=now,
            article_count=trend.article_count,
            source_count=trend.source_count,
            strength_score=trend.strength_score,
            momentum_score=trend.momentum_score,
            status=trend.status,
        )
        db.add(snapshot)

        await db.flush()
        return trend, is_new
