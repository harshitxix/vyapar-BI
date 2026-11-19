from backend.app.models.base import Base
from backend.app.models.source import Source
from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.models.ingestion_run import IngestionRun
from backend.app.models.trend import ArticleEmbedding, Trend, TrendArticle, TrendSnapshot, TrendAnalysisRun
from backend.app.models.personalization import (
    User,
    UserMarketProfile,
    CanonicalEntity,
    UserEntityFollow,
    UserTopicPreference,
    UserFeedPreferences,
    UserInteractionEvent,
    UserLearnedPreference,
)

__all__ = [
    "Base",
    "Source",
    "Article",
    "ArticleEnrichment",
    "IngestionRun",
    "ArticleEmbedding",
    "Trend",
    "TrendArticle",
    "TrendSnapshot",
    "TrendAnalysisRun",
    "User",
    "UserMarketProfile",
    "CanonicalEntity",
    "UserEntityFollow",
    "UserTopicPreference",
    "UserFeedPreferences",
    "UserInteractionEvent",
    "UserLearnedPreference",
]
