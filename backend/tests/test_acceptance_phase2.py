import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.config.settings import settings
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.services.ai.enrichment_service import EnrichmentService
from backend.app.services.ai.providers.mock_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_enrichment_service_with_mock():
    """Verify end-to-end enrichment service updates database properly."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Create a test article
        article_id = f"test_art_{uuid.uuid4().hex[:8]}"
        article = Article(
            id=article_id,
            source_id="et-retail-rss",
            source_name="ET Retail",
            source_domain="retail.economictimes.indiatimes.com",
            title="Blinkit expands dark stores to tier 2 cities in Uttar Pradesh",
            description="Quick commerce delivery platform Blinkit announces opening of 50 new dark store fulfillment centers.",
            original_url=f"https://retail.economictimes.indiatimes.com/news/{article_id}",
            canonical_url=f"https://retail.economictimes.indiatimes.com/news/{article_id}",
            canonical_url_hash=f"hash_{article_id}",
            normalized_title_hash=f"title_hash_{article_id}",
            published_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
            region="india",
            business_domain="retail",
            extraction_method="rss",
            status="published",
        )
        session.add(article)
        await session.commit()

        # Run enrichment service with MockLLMProvider
        service = EnrichmentService(provider=MockLLMProvider())
        enriched = await service.enrich_article(article_id=article_id, db=session)

        assert enriched is not None
        assert enriched.status == "completed"
        assert enriched.summary is not None
        assert enriched.primary_domain in ["retail", "fmcg", "grocery"]
        assert enriched.relevance_score is not None and enriched.relevance_score > 0.5
        assert len(enriched.topics) >= 2
        assert len(enriched.entities) >= 1
        assert enriched.latency_ms > 0

        # Clean up test article
        await session.delete(article)
        await session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_ai_status_and_feed_api():
    """Verify /admin/ai/status and /feed API serializes AI enrichment."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test /admin/ai/status
        status_res = await ac.get("/admin/ai/status")
        assert status_res.status_code == 200
        data = status_res.json()
        assert "total_articles" in data
        assert "enrichment_status_breakdown" in data
        assert "metrics" in data

        # Test /feed endpoint
        feed_res = await ac.get("/feed?limit=5")
        assert feed_res.status_code == 200
        feed_data = feed_res.json()
        assert feed_data["status"] == "success"
        assert "items" in feed_data
        assert isinstance(feed_data["items"], list)

    app.dependency_overrides.clear()
    await engine.dispose()
