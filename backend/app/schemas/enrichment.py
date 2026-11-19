from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    COMPANY = "COMPANY"
    BRAND = "BRAND"
    PRODUCT = "PRODUCT"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    MARKET = "MARKET"
    INDUSTRY = "INDUSTRY"


class ArticleType(str, Enum):
    NEWS = "news"
    ANALYSIS = "analysis"
    EARNINGS = "earnings"
    POLICY = "policy"
    INTERVIEW = "interview"
    OTHER = "other"


class EnrichmentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EntityItem(BaseModel):
    name: str = Field(description="Name of the entity")
    type: EntityType = Field(description="Type of the named entity")


class KeyEventItem(BaseModel):
    type: str = Field(description="Type of business event (e.g., product_launch, company_expansion, funding, price_change)")
    description: str = Field(description="Brief factual description of the event")
    date: Optional[str] = Field(default=None, description="Date or timeframe of the event if mentioned")


class EnrichmentOutput(BaseModel):
    """Structured LLM extraction payload."""
    summary: str = Field(description="2-4 sentence objective, factual summary without speculation")
    primary_domain: str = Field(description="Primary business domain (e.g., grocery, retail, fmcg, technology, electronics, restaurants, logistics, general_business)")
    secondary_domains: List[str] = Field(default_factory=list, description="Secondary domain classifications")
    category: str = Field(description="Primary category (e.g., Market, Consumer, Pricing, Product Launch, Regulation, Supply Chain, Expansion)")
    subcategory: Optional[str] = Field(default=None, description="Specific subcategory")
    article_type: ArticleType = Field(default=ArticleType.NEWS, description="Type of the article")
    topics: List[str] = Field(default_factory=list, description="3-8 normalized, reusable topic strings")
    keywords: List[str] = Field(default_factory=list, description="Key search keywords without generic stopwords")
    entities: List[EntityItem] = Field(default_factory=list, description="Extracted named entities")
    events: List[KeyEventItem] = Field(default_factory=list, description="Discrete business events")
    relevance_score: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0 relevance to retail/kirana/small business owners in India")
    confidence: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0 confidence estimate of classification")


class EnrichmentResult(BaseModel):
    """Full execution result from LLM provider including observability metrics."""
    enrichment: Optional[EnrichmentOutput] = None
    model: str
    prompt_version: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    estimated_cost: float = 0.0
    status: EnrichmentStatus = EnrichmentStatus.COMPLETED
    error_message: Optional[str] = None


class ArticleEnrichmentRead(BaseModel):
    """API response schema for Article Enrichment."""
    id: str
    article_id: str
    status: EnrichmentStatus
    summary: Optional[str] = None
    primary_domain: Optional[str] = None
    secondary_domains: Optional[List[str]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    article_type: Optional[ArticleType] = None
    topics: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    entities: Optional[List[Any]] = None
    events: Optional[List[Any]] = None
    relevance_score: Optional[float] = None
    confidence: Optional[float] = None
    model: str
    prompt_version: str
    latency_ms: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
