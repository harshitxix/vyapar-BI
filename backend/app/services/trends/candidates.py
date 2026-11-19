from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment


class CandidateArticle:
    def __init__(
        self,
        article: Article,
        enrichment: Optional[ArticleEnrichment],
        embedding: Optional[List[float]] = None,
    ):
        self.article = article
        self.enrichment = enrichment
        self.embedding = embedding
        self.id = article.id
        self.published_at = article.published_at
        self.source_id = article.source_id
        self.source_name = article.source_name
        self.domain = (enrichment.primary_domain if enrichment and enrichment.primary_domain else article.business_domain) or "retail"
        self.region = article.region or "india"
        self.topics = [str(t).lower().strip() for t in (enrichment.topics if enrichment and enrichment.topics else []) if t]
        
        # Extract entity strings
        self.entities = []
        if enrichment and enrichment.entities:
            for e in enrichment.entities:
                if isinstance(e, dict):
                    name = e.get("name") or e.get("entity")
                    if name:
                        self.entities.append(name.lower().strip())
                elif isinstance(e, str):
                    self.entities.append(e.lower().strip())


class CandidateGenerator:
    """
    Generates candidate article groups by filtering relevant time windows,
    market domains, and regions for cluster detection.
    """

    @staticmethod
    async def fetch_candidate_articles(
        db: AsyncSession,
        domain: Optional[str] = None,
        region: Optional[str] = None,
        window_days: int = 14,
        baseline_days: int = 45,
    ) -> Tuple[List[CandidateArticle], List[CandidateArticle]]:
        """
        Fetches:
        1. Recent candidate articles within the active window (e.g. last 14 days).
        2. Historical baseline articles (prior to the active window up to baseline_days) for temporal comparison.
        """
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(days=window_days)
        baseline_cutoff = now - timedelta(days=baseline_days)

        stmt = (
            select(Article)
            .options(
                selectinload(Article.enrichment),
                selectinload(Article.embedding),
            )
            .where(
                and_(
                    Article.published_at >= baseline_cutoff,
                    Article.status == "published",
                )
            )
            .order_by(Article.published_at.desc())
        )

        res = await db.execute(stmt)
        articles = res.scalars().all()
        if not articles:
            return [], []

        # Directly load embeddings for articles to guarantee fresh vectors
        from backend.app.models.trend import ArticleEmbedding
        stmt_emb = select(ArticleEmbedding).where(ArticleEmbedding.article_id.in_([a.id for a in articles]))
        res_emb = await db.execute(stmt_emb)
        emb_map = {e.article_id: list(e.embedding) if e.embedding is not None else None for e in res_emb.scalars().all()}

        recent_candidates: List[CandidateArticle] = []
        baseline_candidates: List[CandidateArticle] = []

        for art in articles:
            # Domain filter if requested
            art_domain = (art.enrichment.primary_domain if art.enrichment and art.enrichment.primary_domain else art.business_domain) or "retail"
            if domain and domain.lower() != "all" and art_domain.lower() != domain.lower():
                continue

            # Region filter if requested
            if region and region.lower() != "all" and art.region.lower() != region.lower():
                continue

            emb_vec = emb_map.get(art.id)
            candidate = CandidateArticle(art, art.enrichment, emb_vec)

            # Assign to recent or baseline
            pub_at = art.published_at
            if pub_at.tzinfo is None:
                pub_at = pub_at.replace(tzinfo=timezone.utc)

            if pub_at >= recent_cutoff:
                recent_candidates.append(candidate)
            else:
                baseline_candidates.append(candidate)

        return recent_candidates, baseline_candidates
