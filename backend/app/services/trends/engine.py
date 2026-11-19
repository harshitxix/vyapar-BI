import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.models.trend import Trend, TrendAnalysisRun
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.services.trends.embeddings.service import EmbeddingService
from backend.app.services.trends.candidates import CandidateGenerator, CandidateArticle
from backend.app.services.trends.clustering import ClusteringService
from backend.app.services.trends.temporal import TemporalAnalysisService
from backend.app.services.trends.scoring import TrendScoringService
from backend.app.services.trends.lifecycle import TrendLifecycleService
from backend.app.services.trends.synthesis import TrendSynthesisService
from backend.app.services.trends.persistence import TrendPersistenceService
from backend.app.services.ai.providers.groq_provider import GroqAIProvider
from backend.app.services.ai.providers.mock_provider import MockAIProvider
from backend.app.config.settings import settings

logger = logging.getLogger("vyapar.trends.engine")


class TrendEngine:
    """
    Central Market Trend Intelligence Engine for Vyapar.
    Orchestrates embedding, clustering, temporal analysis, scoring,
    and LLM synthesis.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        clustering_service: Optional[ClusteringService] = None,
        synthesis_service: Optional[TrendSynthesisService] = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.clustering_service = clustering_service or ClusteringService()
        
        if synthesis_service is None:
            # Check configured AI provider
            provider_type = getattr(settings, "AI_PROVIDER", "groq").lower()
            if provider_type == "groq" and getattr(settings, "GROQ_API_KEY", None):
                ai_prov = GroqAIProvider()
            else:
                ai_prov = MockAIProvider()
            self.synthesis_service = TrendSynthesisService(ai_provider=ai_prov)
        else:
            self.synthesis_service = synthesis_service

    async def run_trend_detection(
        self,
        db: AsyncSession,
        domain: Optional[str] = None,
        region: Optional[str] = "india",
        window_days: int = 14,
        baseline_days: int = 45,
    ) -> TrendAnalysisRun:
        """
        Executes a complete trend detection analysis run across enriched articles.
        """
        start_time = time.time()
        now = datetime.now(timezone.utc)
        run_id = str(uuid.uuid4())

        run_record = TrendAnalysisRun(
            run_id=run_id,
            started_at=now,
            domain=domain,
            region=region,
            window_days=window_days,
            status="running",
        )
        db.add(run_record)
        await db.flush()

        try:
            logger.info(f"Starting Trend Detection Run [{run_id}] (domain={domain}, region={region}, window={window_days}d)")

            # Step 1: Fetch candidate articles
            recent_cands, baseline_cands = await CandidateGenerator.fetch_candidate_articles(
                db=db,
                domain=domain,
                region=region,
                window_days=window_days,
                baseline_days=baseline_days,
            )

            all_cands = recent_cands + baseline_cands
            run_record.articles_considered = len(recent_cands)

            if len(recent_cands) < 3:
                logger.info(f"Run [{run_id}]: Insufficient recent articles ({len(recent_cands)}), terminating run cleanly.")
                run_record.finished_at = datetime.now(timezone.utc)
                run_record.duration_ms = int((time.time() - start_time) * 1000)
                run_record.status = "completed"
                await db.commit()
                return run_record

            # Step 2: Ensure all candidates have embeddings
            unembedded = [(c.article, c.enrichment) for c in all_cands if c.embedding is None]
            if unembedded:
                logger.info(f"Run [{run_id}]: Generating embeddings for {len(unembedded)} articles...")
                await self.embedding_service.embed_and_store_articles(db, unembedded)
                await db.commit()
                
                # Reload candidates with their new embeddings
                recent_cands, baseline_cands = await CandidateGenerator.fetch_candidate_articles(
                    db=db,
                    domain=domain,
                    region=region,
                    window_days=window_days,
                    baseline_days=baseline_days,
                )

            # Step 3: Cluster recent articles
            clusters = self.clustering_service.cluster_articles(recent_cands)
            run_record.candidate_clusters = len(clusters)
            logger.info(f"Run [{run_id}]: Detected {len(clusters)} candidate clusters.")

            new_trends_count = 0
            updated_trends_count = 0
            valid_trends_count = 0
            discarded_count = 0

            # Step 4: Analyze, score, synthesize, and persist each cluster
            for cluster in clusters:
                # Temporal metrics
                temporal = TemporalAnalysisService.analyze_cluster_temporal(
                    cluster=cluster,
                    baseline_articles=baseline_cands,
                    recent_window_days=window_days,
                    baseline_window_days=baseline_days,
                )

                # Deterministic scoring
                scores = TrendScoringService.score_trend(cluster, temporal)

                # Quality / Noise rejection filter:
                # Require min 3 articles, min 2 sources, strength >= 0.20
                if cluster.article_count < 3 or cluster.unique_source_count < 2 or scores.strength_score < 0.20:
                    discarded_count += 1
                    continue

                # Deterministic lifecycle
                status = TrendLifecycleService.determine_lifecycle_status(cluster, temporal, scores)

                # LLM / Grounded Synthesis
                target_domain = domain or cluster.articles[0].domain or "retail"
                target_region = region or cluster.articles[0].region or "india"

                synthesis = await self.synthesis_service.synthesize_trend(
                    cluster=cluster,
                    temporal=temporal,
                    scores=scores,
                    domain=target_domain,
                    region=target_region,
                )

                # Persistence & Trend snapshotting
                _, is_new = await TrendPersistenceService.match_or_create_trend(
                    db=db,
                    cluster=cluster,
                    temporal=temporal,
                    scores=scores,
                    synthesis=synthesis,
                    status=status,
                    domain=target_domain,
                    region=target_region,
                )

                valid_trends_count += 1
                if is_new:
                    new_trends_count += 1
                else:
                    updated_trends_count += 1

            # Complete run record
            run_record.valid_trends = valid_trends_count
            run_record.new_trends = new_trends_count
            run_record.updated_trends = updated_trends_count
            run_record.discarded_clusters = discarded_count
            run_record.finished_at = datetime.now(timezone.utc)
            run_record.duration_ms = int((time.time() - start_time) * 1000)
            run_record.status = "completed"

            await db.commit()
            logger.info(
                f"Completed Trend Detection Run [{run_id}] in {run_record.duration_ms}ms: "
                f"{new_trends_count} new trends, {updated_trends_count} updated trends."
            )
            return run_record

        except Exception as e:
            logger.exception(f"Error during trend detection run [{run_id}]: {e}")
            await db.rollback()
            run_record.status = "failed"
            run_record.error_message = str(e)
            run_record.finished_at = datetime.now(timezone.utc)
            run_record.duration_ms = int((time.time() - start_time) * 1000)
            
            # Save failure status in separate commit
            try:
                db.add(run_record)
                await db.commit()
            except Exception:
                pass
            raise
