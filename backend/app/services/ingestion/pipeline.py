import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.source import Source
from backend.app.models.article import Article
from backend.app.models.ingestion_run import IngestionRun
from backend.app.adapters import get_adapter
from backend.app.schemas.article import CanonicalArticle

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Coordinates multi-source ingestion, canonicalization, deduplication,
    storage, source health tracking, and run reporting.
    """

    async def ingest_source(self, db: AsyncSession, source: Source) -> Dict[str, Any]:
        """
        Executes ingestion for a single source with error isolation.
        """
        source_id = str(source.id)
        source_domain = str(source.domain)
        source_name = str(source.name)
        source_type = str(source.source_type)
        source_regions = list(source.regions) if source.regions else ["india"]
        source_domains = list(source.business_domains) if source.business_domains else ["retail"]

        start_time = time.time()
        discovered_count = 0
        inserted_count = 0
        duplicate_count = 0
        rejected_count = 0
        error_msg = None

        try:
            adapter = get_adapter(source_type)
            # 1. Fetch
            payload = await adapter.fetch(source)
            response_time_ms = int((time.time() - start_time) * 1000)

            # 2. Parse
            raw_articles = adapter.parse(payload, source)
            discovered_count = len(raw_articles)

            # 3. Process each article
            for raw in raw_articles:
                # Normalize
                canonical = adapter.normalize(raw, source)

                # Validate
                if not adapter.validate(canonical):
                    rejected_count += 1
                    continue

                # Deduplicate: Check canonical URL hash
                existing_query = select(Article.id).where(
                    Article.canonical_url_hash == canonical.canonical_url_hash
                )
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none() is not None:
                    duplicate_count += 1
                    continue

                # Optional title hash check for same source
                title_query = select(Article.id).where(
                    Article.source_id == source_id,
                    Article.normalized_title_hash == canonical.normalized_title_hash
                )
                title_result = await db.execute(title_query)
                if title_result.scalar_one_or_none() is not None:
                    duplicate_count += 1
                    continue

                # Store article in DB
                db_article = Article(
                    id=canonical.id or str(uuid.uuid4()),
                    source_id=source_id,
                    source_name=source_name,
                    source_domain=source_domain,
                    title=canonical.title,
                    description=canonical.description,
                    author=canonical.author,
                    original_url=canonical.original_url,
                    canonical_url=canonical.canonical_url,
                    canonical_url_hash=canonical.canonical_url_hash,
                    normalized_title_hash=canonical.normalized_title_hash,
                    fingerprint=canonical.fingerprint,
                    image_url=canonical.image_url,
                    published_at=canonical.published_at,
                    fetched_at=canonical.fetched_at,
                    language=canonical.language,
                    region=canonical.region,
                    business_domain=canonical.business_domain,
                    category=canonical.category,
                    subcategory=canonical.subcategory,
                    content_type=canonical.content_type,
                    extraction_method=canonical.extraction_method,
                    status=canonical.status,
                )
                db.add(db_article)
                inserted_count += 1

            # Update Source Health - Success
            source.last_checked = datetime.now(timezone.utc)
            source.last_success = datetime.now(timezone.utc)
            source.failure_count = 0
            source.status = "healthy"
            source.last_response_time_ms = response_time_ms
            source.last_article_count = inserted_count

            await db.commit()

            logger.info(
                f"SOURCE={source_domain} METHOD={source_type} "
                f"DURATION={response_time_ms}ms DISCOVERED={discovered_count} "
                f"INSERTED={inserted_count} DUPLICATES={duplicate_count} STATUS=success"
            )

            return {
                "source_id": source_id,
                "status": "success",
                "discovered": discovered_count,
                "inserted": inserted_count,
                "duplicates": duplicate_count,
                "rejected": rejected_count,
                "response_time_ms": response_time_ms
            }

        except Exception as e:
            await db.rollback()
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error(f"Ingestion failed for source {source_id} ({source_domain}): {error_msg}")

            # Re-fetch source to update failure status cleanly
            try:
                src_res = await db.execute(select(Source).where(Source.id == source_id))
                src_obj = src_res.scalar_one_or_none()
                if src_obj:
                    src_obj.last_checked = datetime.now(timezone.utc)
                    src_obj.last_failure = datetime.now(timezone.utc)
                    src_obj.failure_count = (src_obj.failure_count or 0) + 1
                    src_obj.status = "degraded" if src_obj.failure_count < 3 else "failed"
                    src_obj.last_response_time_ms = response_time_ms
                    await db.commit()
            except Exception as health_err:
                logger.warning(f"Could not update source failure health: {health_err}")

            return {
                "source_id": source_id,
                "status": "failed",
                "discovered": discovered_count,
                "inserted": inserted_count,
                "duplicates": duplicate_count,
                "rejected": rejected_count,
                "error": error_msg,
                "response_time_ms": response_time_ms
            }

    async def run_pipeline(
        self,
        db: AsyncSession,
        trigger_type: str = "manual",
        source_id: Optional[str] = None,
        domain_filter: Optional[str] = None
    ) -> IngestionRun:
        """
        Executes a complete ingestion run across all matching active sources.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Query active sources
        query = select(Source).where(Source.active == True)
        if source_id:
            query = query.where(Source.id == source_id)
        
        result = await db.execute(query)
        sources = list(result.scalars().all())

        if domain_filter:
            sources = [
                s for s in sources 
                if s.business_domains and domain_filter in s.business_domains
            ]

        sources_attempted = len(sources)
        sources_succeeded = 0
        sources_failed = 0
        articles_discovered = 0
        articles_inserted = 0
        articles_duplicate = 0
        articles_rejected = 0
        results = []

        for source in sources:
            res = await self.ingest_source(db, source)
            results.append(res)
            if res["status"] == "success":
                sources_succeeded += 1
            else:
                sources_failed += 1

            articles_discovered += res.get("discovered", 0)
            articles_inserted += res.get("inserted", 0)
            articles_duplicate += res.get("duplicates", 0)
            articles_rejected += res.get("rejected", 0)

        finished_at = datetime.now(timezone.utc)
        status = "completed" if sources_failed == 0 else "completed_with_errors"

        ingestion_run = IngestionRun(
            id=run_id,
            trigger_type=trigger_type,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            sources_attempted=sources_attempted,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            articles_discovered=articles_discovered,
            articles_inserted=articles_inserted,
            articles_duplicate=articles_duplicate,
            articles_rejected=articles_rejected,
            error_details={"runs": results}
        )
        db.add(ingestion_run)
        await db.commit()

        return ingestion_run
