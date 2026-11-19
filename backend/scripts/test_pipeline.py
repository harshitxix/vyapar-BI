import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.database.session import AsyncSessionLocal
from backend.app.services.ingestion.pipeline import IngestionService
from backend.app.models.article import Article
from sqlalchemy import select, func


async def test_pipeline():
    print("\n=======================================================")
    print("STEP 4 ACCEPTANCE TEST: ONE SOURCE END-TO-END PIPELINE")
    print("=======================================================\n")

    service = IngestionService()

    async with AsyncSessionLocal() as session:
        # Run 1: First Ingestion Run
        print("1. Running ingestion for primary source (et-retail-rss)...")
        run_1 = await service.run_pipeline(session, trigger_type="manual", source_id="et-retail-rss")
        print(f"   ✓ Ingestion Run #1 Complete: Status = {run_1.status}")
        print(f"   ✓ Discovered: {run_1.articles_discovered}")
        print(f"   ✓ Inserted:   {run_1.articles_inserted}")
        print(f"   ✓ Duplicates: {run_1.articles_duplicate}")
        print(f"   ✓ Rejected:   {run_1.articles_rejected}")

        assert run_1.articles_inserted > 0, "Expected at least 1 article inserted on first run!"

        # Query and display top 3 inserted articles
        print("\n2. Querying stored canonical articles from PostgreSQL...")
        result = await session.execute(
            select(Article).where(Article.source_id == "et-retail-rss").order_by(Article.published_at.desc()).limit(3)
        )
        articles = result.scalars().all()
        for idx, art in enumerate(articles, 1):
            print(f"\n   [Article {idx}]")
            print(f"   - Title:        {art.title[:75]}...")
            print(f"   - Domain:       {art.business_domain}")
            print(f"   - Published:    {art.published_at} (UTC)")
            print(f"   - CanonicalURL: {art.canonical_url}")
            print(f"   - URL Hash:     {art.canonical_url_hash[:16]}...")
            print(f"   - Title Hash:   {art.normalized_title_hash[:16]}...")
            print(f"   - Image URL:    {art.image_url}")

        # Run 2: Deduplication Test
        print("\n3. Testing Deduplication (Running ingestion again on the same source)...")
        run_2 = await service.run_pipeline(session, trigger_type="manual", source_id="et-retail-rss")
        print(f"   ✓ Ingestion Run #2 Complete: Status = {run_2.status}")
        print(f"   ✓ Discovered: {run_2.articles_discovered}")
        print(f"   ✓ Inserted:   {run_2.articles_inserted}")
        print(f"   ✓ Duplicates: {run_2.articles_duplicate}")

        assert run_2.articles_inserted == 0, f"Expected 0 new insertions, but got {run_2.articles_inserted}"
        assert run_2.articles_duplicate > 0, f"Expected duplicate detection, got {run_2.articles_duplicate}"
        print("\n[SUCCESS] DEDUPLICATION VERIFIED! All previously inserted articles were identified as duplicates and rejected.")

        # Total article count in DB
        count_res = await session.execute(select(func.count(Article.id)))
        total_count = count_res.scalar()
        print(f"\n[INFO] Total Articles in PostgreSQL Database: {total_count}")
        print("\n[PASSED] MILESTONE 1 (STEP 2, 3, 4) PASSED PERFECTLY!\n")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
