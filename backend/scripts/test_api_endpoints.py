import asyncio
import sys
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def test_api():
    base_url = "http://127.0.0.1:8000"
    print("\n=======================================================")
    print("STEP 6, 7, 8 ACCEPTANCE TEST: REST API & SCHEDULER")
    print("=======================================================\n")

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # 1. Health Check
        print("1. Testing GET /health...")
        res = await client.get("/health")
        print(f"   Status Code: {res.status_code}")
        print(f"   Response:    {res.json()}")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["database"] == "healthy"
        assert res.json()["scheduler_active"] is True

        # 2. List Sources
        print("\n2. Testing GET /sources...")
        res = await client.get("/sources")
        print(f"   Status Code: {res.status_code}")
        sources = res.json()
        print(f"   Found {len(sources)} registered sources.")
        assert len(sources) >= 5

        # 3. Sources Health Status
        print("\n3. Testing GET /sources/status...")
        res = await client.get("/sources/status")
        print(f"   Status Code: {res.status_code}")
        health_data = res.json()
        print(f"   Total: {health_data['total_sources']} | Healthy: {health_data['healthy']} | Degraded/Failed: {health_data['failed'] + health_data['degraded']}")

        # 4. List Articles with Filters
        print("\n4. Testing GET /articles (Filtered by grocery domain)...")
        res = await client.get("/articles", params={"business_domain": "grocery", "limit": 5})
        print(f"   Status Code: {res.status_code}")
        articles_data = res.json()
        print(f"   Total Matching: {articles_data['total']}, Returned: {len(articles_data['items'])}")
        assert articles_data["total"] > 0
        first_art = articles_data["items"][0]
        print(f"   Sample Headline: {first_art['title'][:70]}...")

        # 5. Mobile Feed Endpoint
        print("\n5. Testing GET /feed (Mobile Feed with cursor)...")
        res = await client.get("/feed", params={"limit": 5})
        print(f"   Status Code: {res.status_code}")
        feed_data = res.json()
        print(f"   Status: {feed_data['status']}, Count: {feed_data['count']}, Has More: {feed_data['has_more']}")
        print(f"   Next Cursor: {feed_data['next_cursor']}")
        assert len(feed_data["items"]) > 0

        # 6. Manual Refresh Ingestion Trigger
        print("\n6. Testing POST /ingestion/refresh (Non-blocking background refresh)...")
        res = await client.post("/ingestion/refresh", json={"domain": "retail"})
        print(f"   Status Code: {res.status_code}")
        print(f"   Response:    {res.json()}")
        assert res.status_code == 202

        # 7. Ingestion Run Status
        print("\n7. Testing GET /ingestion/status...")
        await asyncio.sleep(2)  # brief wait for background task progress
        res = await client.get("/ingestion/status")
        print(f"   Status Code: {res.status_code}")
        runs = res.json()
        print(f"   Found {len(runs)} recorded ingestion runs.")
        if runs:
            print(f"   Latest Run: ID={runs[0]['id']} | Status={runs[0]['status']} | Trigger={runs[0]['trigger_type']}")

        print("\n=======================================================")
        print("[PASSED] ALL API ENDPOINTS & SCHEDULER VERIFIED SUCCESSFULLY!")
        print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(test_api())
