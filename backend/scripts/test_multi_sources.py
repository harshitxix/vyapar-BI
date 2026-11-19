import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.database.session import AsyncSessionLocal
from backend.app.services.ingestion.pipeline import IngestionService
from backend.app.models.source import Source
from backend.app.models.article import Article
from sqlalchemy import select, func


async def test_multi_source_ingestion():
    print("\n=======================================================")
    print("STEP 5 ACCEPTANCE TEST: MULTI-SOURCE INGESTION CYCLE")
    print("=======================================================\n")

    service = IngestionService()

    async with AsyncSessionLocal() as session:
        # Check registered sources
        sources_res = await session.execute(select(Source))
        sources = sources_res.scalars().all()
        print(f"[INFO] Registered Sources in Database: {len(sources)}")
        for s in sources:
            print(f"  - {s.name} ({s.id}) | Type: {s.source_type} | Interval: {s.refresh_interval}s")

        print("\n1. Running Full Ingestion Pipeline across all registered sources...")
        run = await service.run_pipeline(session, trigger_type="manual")

        print(f"\n[INFO] Pipeline Run Results:")
        print(f"   - Run ID:             {run.id}")
        print(f"   - Status:             {run.status}")
        print(f"   - Sources Attempted:  {run.sources_attempted}")
        print(f"   - Sources Succeeded:  {run.sources_succeeded}")
        print(f"   - Sources Failed:     {run.sources_failed}")
        print(f"   - Total Discovered:   {run.articles_discovered}")
        print(f"   - Total Inserted:     {run.articles_inserted}")
        print(f"   - Total Duplicates:   {run.articles_duplicate}")
        print(f"   - Total Rejected:     {run.articles_rejected}")

        assert run.sources_succeeded > 0, "Expected at least 1 source to succeed!"

        # Query counts per business domain
        print("\n2. Breakdown by Business Domain in PostgreSQL:")
        domain_query = select(Article.business_domain, func.count(Article.id)).group_by(Article.business_domain)
        domain_counts = await session.execute(domain_query)
        for domain, count in domain_counts.all():
            print(f"   - {domain.capitalize()}: {count} articles")

        # Query total count
        count_res = await session.execute(select(func.count(Article.id)))
        total = count_res.scalar()
        print(f"\n[SUCCESS] Total Canonical Articles Stored: {total}")
        print("\n[PASSED] STEP 5 (MULTI-SOURCE INGESTION) PASSED SUCCESSFULLY!\n")


if __name__ == "__main__":
    asyncio.run(test_multi_source_ingestion())
