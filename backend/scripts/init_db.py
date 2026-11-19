import asyncio
import sys
import os

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database.session import init_db, async_engine
from backend.app.models import Source, Article, IngestionRun
from sqlalchemy import text


async def main():
    print("Testing PostgreSQL connection...")
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"Connected to PostgreSQL successfully! Version: {version}")

        print("Creating database tables (sources, articles, ingestion_runs)...")
        await init_db()
        print("All tables created successfully in PostgreSQL!")
    except Exception as e:
        print(f"Database initialization error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
