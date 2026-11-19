import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database.session import AsyncSessionLocal, init_db
from backend.app.models.source import Source
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.models.trend import Trend, ArticleEmbedding, TrendAnalysisRun
from backend.app.services.trends.engine import TrendEngine
from backend.app.services.trends.embeddings.mock_provider import MockEmbeddingProvider
from backend.app.services.trends.embeddings.service import EmbeddingService
from backend.app.services.ai.providers.mock_provider import MockAIProvider
from backend.app.services.trends.synthesis import TrendSynthesisService


@pytest.mark.asyncio
async def test_phase3_end_to_end_pipeline():
    await init_db()
    
    # 1. Setup test sources and articles in DB
    now = datetime.now(timezone.utc)
    mock_emb_service = EmbeddingService(provider=MockEmbeddingProvider(dimension=384))
    mock_synthesis_service = TrendSynthesisService(ai_provider=MockAIProvider())
    trend_engine = TrendEngine(
        embedding_service=mock_emb_service,
        synthesis_service=mock_synthesis_service,
    )

    async with AsyncSessionLocal() as session:
        # Create sources
        src1 = Source(
            id=f"src_test_1_{uuid.uuid4().hex[:6]}",
            name="Economic Times Retail",
            domain="economictimes.indiatimes.com",
            base_url="https://economictimes.indiatimes.com",
            feed_url="http://test.com/rss1",
            source_type="rss",
            active=True,
            priority=1,
        )
        src2 = Source(
            id=f"src_test_2_{uuid.uuid4().hex[:6]}",
            name="Retail4Growth",
            domain="retail4growth.com",
            base_url="https://retail4growth.com",
            feed_url="http://test.com/rss2",
            source_type="rss",
            active=True,
            priority=2,
        )
        session.add_all([src1, src2])
        await session.flush()

        # Seed 4 semantically similar articles on quick commerce
        topic_cluster_articles = []
        for i in range(4):
            art = Article(
                id=f"art_qc_{i}_{uuid.uuid4().hex[:6]}",
                source_id=src1.id if i % 2 == 0 else src2.id,
                source_name=src1.name if i % 2 == 0 else src2.name,
                source_domain=src1.domain if i % 2 == 0 else src2.domain,
                title=f"Quick commerce dark stores expand 10-minute grocery network {i}",
                description="Hyperlocal delivery players expand dark store footprint across top Indian metros.",
                original_url=f"http://test.com/qc_{i}_{uuid.uuid4().hex[:6]}",
                canonical_url=f"http://test.com/qc_{i}_{uuid.uuid4().hex[:6]}",
                canonical_url_hash=uuid.uuid4().hex,
                normalized_title_hash=uuid.uuid4().hex,
                published_at=now - timedelta(days=i),
                region="india",
                business_domain="grocery",
                extraction_method="rss",
                status="published",
            )
            enr = ArticleEnrichment(
                id=f"enr_qc_{i}_{uuid.uuid4().hex[:6]}",
                article_id=art.id,
                status="completed",
                summary=f"Dark store rapid expansion by quick commerce operators in metro cities {i}.",
                primary_domain="grocery",
                category="Market",
                subcategory="Expansion",
                topics=["quick commerce", "dark stores", "grocery delivery"],
                entities=["Blinkit", "Zepto", "India"],
                relevance_score=0.92,
                confidence=0.95,
                model="test",
                prompt_version="v1",
            )
            session.add_all([art, enr])
            topic_cluster_articles.append(art)

        await session.commit()

        # 2. Run Trend Detection Engine
        run_record = await trend_engine.run_trend_detection(
            db=session,
            domain="grocery",
            region="india",
            window_days=14,
        )

        assert run_record.status == "completed"
        assert run_record.valid_trends >= 1
        assert (run_record.new_trends + run_record.updated_trends) >= 1

    # 3. Test API Endpoints using AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /trends
        resp = await client.get("/trends?domain=grocery&region=india")
        assert resp.status_code == 200
        trends_data = resp.json()
        assert len(trends_data) >= 1
        
        target_trend = trends_data[0]
        trend_id = target_trend["id"]
        assert target_trend["article_count"] >= 3
        assert target_trend["status"] in ["emerging", "growing", "established"]
        assert 0.0 <= target_trend["strength_score"] <= 1.0

        # GET /trends/{trend_id}
        resp_detail = await client.get(f"/trends/{trend_id}")
        assert resp_detail.status_code == 200
        detail_data = resp_detail.json()
        assert detail_data["why_emerging"] is not None
        assert len(detail_data["key_developments"]) > 0
        assert len(detail_data["supporting_articles"]) >= 3

        # Verify no business advice / recommendations in trend payload
        text_dump = str(detail_data).lower()
        assert "you should" not in text_dump
        assert "your store should" not in text_dump
        assert "increase your inventory" not in text_dump

        # GET /trends/{trend_id}/timeline
        resp_timeline = await client.get(f"/trends/{trend_id}/timeline")
        assert resp_timeline.status_code == 200
        timeline_data = resp_timeline.json()
        assert len(timeline_data) >= 1

        # GET /admin/trends/runs
        resp_runs = await client.get("/admin/trends/runs")
        assert resp_runs.status_code == 200
        runs_data = resp_runs.json()
        assert len(runs_data) >= 1
        assert runs_data[0]["status"] == "completed"
