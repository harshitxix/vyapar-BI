import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database.session import AsyncSessionLocal, async_engine
from backend.app.models.source import Source
from sqlalchemy import select


SEED_SOURCES = [
    {
        "id": "et-retail-rss",
        "name": "Economic Times Retail",
        "domain": "retail.economictimes.indiatimes.com",
        "base_url": "https://retail.economictimes.indiatimes.com",
        "source_type": "rss",
        "feed_url": "https://retail.economictimes.indiatimes.com/rss/topstories",
        "api_endpoint": None,
        "business_domains": ["retail", "grocery", "fmcg"],
        "regions": ["india"],
        "language": "en",
        "refresh_interval": 600,
        "priority": 1,
        "active": True
    },
    {
        "id": "mint-companies-rss",
        "name": "Livemint Retail & Industry",
        "domain": "livemint.com",
        "base_url": "https://www.livemint.com",
        "source_type": "rss",
        "feed_url": "https://www.livemint.com/rss/companies",
        "api_endpoint": None,
        "business_domains": ["retail", "business", "manufacturing"],
        "regions": ["india"],
        "language": "en",
        "refresh_interval": 900,
        "priority": 1,
        "active": True
    },
    {
        "id": "inc42-commerce-rss",
        "name": "Inc42 Quick Commerce & Tech",
        "domain": "inc42.com",
        "base_url": "https://inc42.com",
        "source_type": "rss",
        "feed_url": "https://inc42.com/feed/",
        "api_endpoint": None,
        "business_domains": ["grocery", "retail", "technology"],
        "regions": ["india"],
        "language": "en",
        "refresh_interval": 1200,
        "priority": 2,
        "active": True
    },
    {
        "id": "financial-express-industry",
        "name": "Financial Express Industry & Retail",
        "domain": "financialexpress.com",
        "base_url": "https://www.financialexpress.com",
        "source_type": "rss",
        "feed_url": "https://www.financialexpress.com/industry/feed/",
        "api_endpoint": None,
        "business_domains": ["retail", "grocery", "business"],
        "regions": ["india"],
        "language": "en",
        "refresh_interval": 900,
        "priority": 2,
        "active": True
    },
    {
        "id": "thehindubusinessline-agri",
        "name": "The Hindu Business Line FMCG & Agri",
        "domain": "thehindubusinessline.com",
        "base_url": "https://www.thehindubusinessline.com",
        "source_type": "rss",
        "feed_url": "https://www.thehindubusinessline.com/economy/agri-business/feeder/default.rss",
        "api_endpoint": None,
        "business_domains": ["grocery", "retail", "fmcg"],
        "regions": ["india"],
        "language": "en",
        "refresh_interval": 900,
        "priority": 2,
        "active": True
    },
    {
        "id": "business-standard-companies",
        "name": "Business Standard Companies",
        "domain": "business-standard.com",
        "base_url": "https://www.business-standard.com",
        "source_type": "rss",
        "feed_url": "https://www.business-standard.com/rss/companies-101.rss",
        "api_endpoint": None,
        "business_domains": ["retail", "business", "manufacturing"],
        "regions": ["india"],
        "language": "en",
        "refresh_interval": 900,
        "priority": 2,
        "active": True
    }
]


async def seed_sources():
    print("Seeding initial sources into PostgreSQL...")
    async with AsyncSessionLocal() as session:
        for s_data in SEED_SOURCES:
            result = await session.execute(select(Source).where(Source.id == s_data["id"]))
            existing = result.scalar_one_or_none()
            if not existing:
                source = Source(**s_data)
                session.add(source)
                print(f"  + Added source: {s_data['name']} ({s_data['id']})")
            else:
                for k, v in s_data.items():
                    setattr(existing, k, v)
                print(f"  * Updated source: {s_data['name']} ({s_data['id']})")
        await session.commit()
    print("Source seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_sources())
