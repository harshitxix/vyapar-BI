import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import settings
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.schemas.enrichment import EnrichmentStatus
from backend.app.services.ai.providers import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Core AI enrichment service orchestrating LLM analysis, prompt injection defense,
    structured validation, and PostgreSQL persistence.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def get_or_create_enrichment_record(
        self, article_id: str, db: AsyncSession
    ) -> ArticleEnrichment:
        """Fetch existing enrichment or initialize a new pending record."""
        stmt = select(ArticleEnrichment).where(ArticleEnrichment.article_id == article_id)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            record = ArticleEnrichment(
                id=f"enr_{uuid.uuid4().hex[:16]}",
                article_id=article_id,
                status="pending",
                model=self.provider.model_name,
                prompt_version=settings.AI_PROMPT_VERSION,
                attempt_count=0,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)

        return record

    async def enrich_article(
        self,
        article_id: str,
        db: AsyncSession,
        force: bool = False,
    ) -> Optional[ArticleEnrichment]:
        """
        Enrich a single article by ID using configured LLM provider.
        """
        # Fetch article
        stmt = select(Article).where(Article.id == article_id)
        res = await db.execute(stmt)
        article = res.scalar_one_or_none()

        if not article:
            logger.warning(f"[Enrichment] Article {article_id} not found in database.")
            return None

        # Fetch or create enrichment record
        record = await self.get_or_create_enrichment_record(article_id, db)

        if record.status == "completed" and not force:
            logger.debug(f"[Enrichment] Article {article_id} already enriched. Skipping.")
            return record

        # Check maximum retry attempts
        if record.attempt_count >= settings.AI_MAX_RETRIES and not force:
            logger.warning(f"[Enrichment] Article {article_id} reached max retry limit ({settings.AI_MAX_RETRIES}).")
            return record

        record.status = "processing"
        record.attempt_count += 1
        record.last_attempt_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            logger.info(f"[Enrichment] Calling LLM ({self.provider.model_name}) for article: '{article.title[:60]}...'")
            result = await self.provider.enrich_article(
                title=article.title,
                description=article.description or "",
                content="",
            )

            if result.status == EnrichmentStatus.COMPLETED and result.enrichment:
                enrichment = result.enrichment
                record.summary = enrichment.summary
                record.primary_domain = enrichment.primary_domain
                record.secondary_domains = enrichment.secondary_domains
                record.category = enrichment.category
                record.subcategory = enrichment.subcategory
                record.article_type = enrichment.article_type.value
                record.topics = enrichment.topics
                record.keywords = enrichment.keywords
                record.entities = [e.model_dump() for e in enrichment.entities]
                record.events = [ev.model_dump() for ev in enrichment.events]
                record.relevance_score = enrichment.relevance_score
                record.confidence = enrichment.confidence

                record.model = result.model
                record.prompt_version = result.prompt_version
                record.input_tokens = result.input_tokens
                record.output_tokens = result.output_tokens
                record.latency_ms = result.latency_ms
                record.estimated_cost = result.estimated_cost
                record.status = "completed"
                record.last_error = None

                # Synchronize AI taxonomy back to canonical article
                if enrichment.primary_domain:
                    article.business_domain = enrichment.primary_domain
                if enrichment.category:
                    article.category = enrichment.category
                if enrichment.subcategory:
                    article.subcategory = enrichment.subcategory

                logger.info(
                    f"[Enrichment Success] Enriched '{article.title[:50]}' | "
                    f"Domain={record.primary_domain} | Relevance={record.relevance_score:.2f} | Latency={record.latency_ms}ms"
                )
            else:
                record.status = "failed"
                record.last_error = result.error_message or "Unknown LLM error"
                logger.error(f"[Enrichment Failed] Article {article_id}: {record.last_error}")

        except Exception as exc:
            record.status = "failed"
            record.last_error = str(exc)
            logger.exception(f"[Enrichment Error] Unhandled exception enriching {article_id}: {exc}")

        await db.commit()
        await db.refresh(record)
        return record

    async def enrich_pending_articles(
        self,
        db: AsyncSession,
        batch_size: int = 5,
    ) -> List[ArticleEnrichment]:
        """
        Query unenriched articles and enrich them in a batch.
        """
        # Find articles that either don't have an enrichment record or have status 'pending' / retriable 'failed'
        stmt = (
            select(Article)
            .outerjoin(ArticleEnrichment, Article.id == ArticleEnrichment.article_id)
            .where(
                (ArticleEnrichment.id.is_(None))
                | (
                    (ArticleEnrichment.status.in_(["pending", "failed"]))
                    & (ArticleEnrichment.attempt_count < settings.AI_MAX_RETRIES)
                )
            )
            .order_by(Article.published_at.desc())
            .limit(batch_size)
        )

        res = await db.execute(stmt)
        articles = res.scalars().all()

        if not articles:
            return []

        logger.info(f"[Enrichment Batch] Found {len(articles)} articles pending enrichment.")
        enriched_records = []
        for article in articles:
            rec = await self.enrich_article(article.id, db)
            if rec:
                enriched_records.append(rec)
            # Gentle delay to respect free tier tokens per minute limits
            await asyncio.sleep(1.2)

        return enriched_records
