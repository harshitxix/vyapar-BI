import asyncio
from sqlalchemy import text
from backend.app.database.session import AsyncSessionLocal


async def cleanup_test_data():
    async with AsyncSessionLocal() as session:
        # Delete trends created during testing
        res_t = await session.execute(text("DELETE FROM trends WHERE name LIKE '%Rapid Expansion%' OR name LIKE 'Emerging Shift%' OR name LIKE 'Test%'"))
        # Delete test articles
        res_a = await session.execute(text("DELETE FROM articles WHERE id LIKE 'art_qc_%' OR id LIKE 'art_test_%' OR title LIKE '%dark stores expand 10-minute%'"))
        # Delete test sources
        res_s = await session.execute(text("DELETE FROM sources WHERE id LIKE 'src_test_%'"))
        # Delete test analysis runs
        await session.execute(text("DELETE FROM trend_analysis_runs WHERE domain = 'grocery' AND candidate_clusters > 0 AND articles_considered <= 4"))
        await session.commit()
        print(f"Cleaned up database: test trends, articles, and sources removed.")


if __name__ == "__main__":
    asyncio.run(cleanup_test_data())
