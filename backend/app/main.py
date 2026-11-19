import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import settings
from backend.app.scheduler.manager import scheduler_manager
from backend.app.api.health import router as health_router
from backend.app.api.sources import router as sources_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.articles import router as articles_router
from backend.app.api.feed import router as feed_router
from backend.app.api.admin_enrichment import router as admin_ai_router
from backend.app.api.trends import router as trends_router, admin_router as admin_trends_router
from backend.app.api.users import router as users_router, taxonomy_router
from backend.app.api.personalization_feed import router as personalization_feed_router
from backend.app.api.interactions import router as interactions_router
from backend.app.database.session import init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vyapar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[LIFESPAN] Starting up Vyapar Market Intelligence API...")
    await init_db()
    # Start APScheduler
    await scheduler_manager.start()
    yield
    logger.info("[LIFESPAN] Shutting down...")
    scheduler_manager.shutdown()


app = FastAPI(
    title="Vyapar Market Intelligence Feed API",
    description="Multi-source market intelligence ingestion and feed pipeline for small retail & businesses.",
    version="0.4.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(personalization_feed_router)
app.include_router(feed_router)
app.include_router(articles_router)
app.include_router(sources_router)
app.include_router(ingestion_router)
app.include_router(admin_ai_router)
app.include_router(trends_router)
app.include_router(admin_trends_router)
app.include_router(users_router)
app.include_router(taxonomy_router)
app.include_router(interactions_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "Vyapar Market Intelligence Feed API",
        "status": "online",
        "docs_url": "/docs"
    }
