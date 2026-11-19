import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.models.personalization import User, UserMarketProfile, CanonicalEntity, UserTopicPreference
from backend.app.api.auth import get_current_user
from backend.app.database.session import get_db


@pytest.fixture(autouse=True)
def mock_lifespan_deps():
    with patch("backend.app.database.session.init_db", new_callable=AsyncMock), \
         patch("backend.app.scheduler.manager.scheduler_manager.start", new_callable=AsyncMock), \
         patch("backend.app.scheduler.manager.scheduler_manager.shutdown", return_value=None):
        yield


@pytest.fixture
def mock_user():
    return User(
        id="usr_test_123",
        email="test_retailer@vyapar.ai",
        username="harshit_retailer",
        is_active=True,
    )


@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    return mock_session


@pytest.mark.asyncio
async def test_taxonomy_endpoint(mock_user, mock_db_session):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/taxonomy/domains")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["domains"]) >= 12
        domain_ids = [d["id"] for d in data["domains"]]
        assert "grocery" in domain_ids
        assert "fashion" in domain_ids

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_entities_endpoint(mock_user, mock_db_session):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    mock_entities = [
        CanonicalEntity(
            id="ent_blinkit",
            name="Blinkit",
            entity_type="COMPANY",
            aliases=["blinkit"],
            domain="grocery",
        ),
        CanonicalEntity(
            id="ent_zepto",
            name="Zepto",
            entity_type="COMPANY",
            aliases=["zepto"],
            domain="grocery",
        ),
    ]

    with patch(
        "backend.app.services.personalization.entity_service.EntityFollowService.list_canonical_entities",
        new_callable=AsyncMock,
        return_value=mock_entities,
    ), patch(
        "backend.app.services.personalization.entity_service.EntityFollowService.get_user_followed_entities",
        new_callable=AsyncMock,
        return_value=[mock_entities[0]],
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/entities")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["name"] == "Blinkit"
            assert data[0]["is_followed"] is True
            assert data[1]["name"] == "Zepto"
            assert data[1]["is_followed"] is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_market_profile_crud(mock_user, mock_db_session):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    now = datetime.now(timezone.utc)
    mock_profile = UserMarketProfile(
        id="prof_1",
        user_id=mock_user.id,
        business_name="Harshit Kirana Store",
        business_domain="grocery",
        business_subdomain="neighborhood_grocery",
        country="India",
        state="Haryana",
        city="Gurugram",
        preferred_language="English",
        created_at=now,
        updated_at=now,
    )

    with patch(
        "backend.app.services.personalization.user_service.UserProfileService.get_profile",
        new_callable=AsyncMock,
        return_value=mock_profile,
    ), patch(
        "backend.app.services.personalization.user_service.UserProfileService.upsert_profile",
        new_callable=AsyncMock,
        return_value=mock_profile,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # GET
            get_resp = await client.get("/users/me/market-profile")
            assert get_resp.status_code == 200
            profile_data = get_resp.json()
            assert profile_data["business_domain"] == "grocery"
            assert profile_data["city"] == "Gurugram"

            # POST (create/replace)
            post_resp = await client.post(
                "/users/me/market-profile",
                json={
                    "business_domain": "grocery",
                    "business_subdomain": "neighborhood_grocery",
                    "country": "India",
                    "state": "Haryana",
                    "city": "Gurugram",
                },
            )
            assert post_resp.status_code == 200
            assert post_resp.json()["business_domain"] == "grocery"

            # PATCH (partial update)
            patch_resp = await client.patch(
                "/users/me/market-profile",
                json={"business_name": "Updated Kirana"},
            )
            assert patch_resp.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_topic_interests_endpoints(mock_user, mock_db_session):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    now = datetime.now(timezone.utc)
    mock_topic = UserTopicPreference(
        id="top_1",
        user_id=mock_user.id,
        topic_id="fmcg",
        preference_score=1.0,
        preference_source="explicit_onboarding",
        is_explicit=True,
        created_at=now,
    )

    with patch(
        "backend.app.services.personalization.user_service.UserProfileService.get_interests",
        new_callable=AsyncMock,
        return_value=[mock_topic],
    ), patch(
        "backend.app.services.personalization.user_service.UserProfileService.add_interest",
        new_callable=AsyncMock,
        return_value=mock_topic,
    ), patch(
        "backend.app.services.personalization.user_service.UserProfileService.remove_interest",
        new_callable=AsyncMock,
        return_value=True,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # GET /users/me/interests
            res = await client.get("/users/me/interests")
            assert res.status_code == 200
            assert len(res.json()) == 1
            assert res.json()[0]["topic_id"] == "fmcg"

            # POST /users/me/interests
            add_res = await client.post(
                "/users/me/interests",
                json={"topic": "fmcg", "preference_score": 1.0},
            )
            assert add_res.status_code == 200
            assert add_res.json()["topic_id"] == "fmcg"

            # DELETE /users/me/interests/fmcg
            del_res = await client.delete("/users/me/interests/fmcg")
            assert del_res.status_code == 200
            assert del_res.json()["removed"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_for_you_feed_endpoint(mock_user, mock_db_session):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    mock_feed_data = {
        "status": "success",
        "count": 2,
        "total_candidates": 15,
        "has_more": False,
        "next_cursor": None,
        "items": [
            {
                "type": "article",
                "id": "art_1",
                "title": "Quick Commerce Grocery Surge in Gurugram",
                "description": "Dark stores seeing highkirana partnership adoption.",
                "source_id": "src_1",
                "source_name": "Inc42",
                "source_domain": "inc42.com",
                "original_url": "https://inc42.com/1",
                "canonical_url": "https://inc42.com/1",
                "image_url": None,
                "published_at": "2026-11-18T10:00:00Z",
                "business_domain": "grocery",
                "category": "retail",
                "subcategory": None,
                "relevance_score": 0.88,
                "enrichment": {
                    "summary": "Quick commerce expanding.",
                    "topics": ["quick commerce", "fmcg"],
                    "entities": [{"name": "Blinkit", "type": "company"}],
                    "relevance_score": 0.9,
                },
                "personalization": {
                    "reasons": ["Relevant to your Grocery business", "Local market update for Gurugram"],
                    "matched_topics": ["quick commerce", "fmcg"],
                    "matched_entities": ["Blinkit"],
                    "signals": {"domain": 1.0, "geography": 1.0},
                },
            },
            {
                "type": "trend",
                "id": "trend_1",
                "title": "Surging Quick Commerce Adoption",
                "description": "Kiranas joining 10-minute grocery delivery hubs.",
                "domain": "grocery",
                "region": "india",
                "category": "Consumer Trend",
                "status": "growing",
                "strength_score": 0.85,
                "user_relevance_score": 0.92,
                "final_score": 0.899,
                "article_count": 8,
                "source_count": 4,
                "personalization": {
                    "reasons": ["Directly aligns with your Grocery market"],
                    "matched_topics": ["quick commerce"],
                    "matched_entities": [],
                },
            },
        ],
        "diagnostics": {
            "latency_ms": 14,
            "articles_scored": 15,
            "trends_scored": 3,
            "user_domain": "grocery",
            "config_version": "v1.0.0",
        },
    }

    with patch(
        "backend.app.services.personalization.engine.personalization_engine.generate_for_you_feed",
        new_callable=AsyncMock,
        return_value=mock_feed_data,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/feed/for-you?limit=10")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["count"] == 2
            items = data["items"]
            assert items[0]["type"] == "article"
            assert items[0]["relevance_score"] == 0.88
            assert "Relevant to your Grocery business" in items[0]["personalization"]["reasons"]
            assert items[1]["type"] == "trend"
            assert items[1]["user_relevance_score"] == 0.92

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_interaction_recording_endpoint(mock_user, mock_db_session):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    mock_event = MagicMock()
    mock_event.id = "evt_12345"
    mock_event.event_type = "article_dwell"
    from datetime import datetime, timezone
    mock_event.created_at = datetime.now(timezone.utc)

    with patch(
        "backend.app.services.personalization.feedback.FeedbackService.record_interaction",
        new_callable=AsyncMock,
        return_value=mock_event,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/interactions",
                json={
                    "event_type": "article_dwell",
                    "article_id": "art_1",
                    "topic_id": "quick_commerce",
                    "source_screen": "for_you",
                },
            )
            assert resp.status_code == 200
            res = resp.json()
            assert res["status"] == "recorded"
            assert res["event_type"] == "article_dwell"
            assert res["id"] == "evt_12345"

    app.dependency_overrides.clear()
