from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CanonicalArticle(BaseModel):
    """Normalized article representation according to section 9 canonical schema."""
    id: Optional[str] = Field(None, description="Generated deterministic or UUID identifier")
    source_id: str = Field(..., description="ID of the source")
    source_name: str = Field(..., description="Name of the source")
    source_domain: str = Field(..., description="Domain of the source")

    title: str = Field(..., min_length=3, description="Article headline/title")
    description: Optional[str] = Field(None, description="Excerpt or short description")
    author: Optional[str] = Field(None, description="Article author")

    original_url: str = Field(..., description="Original raw URL")
    canonical_url: str = Field(..., description="Cleaned canonical URL")
    canonical_url_hash: str = Field(..., description="SHA-256 hash of canonical URL")
    normalized_title_hash: str = Field(..., description="SHA-256 hash of normalized title")
    fingerprint: Optional[str] = Field(None, description="Near-duplicate content fingerprint")

    image_url: Optional[str] = Field(None, description="Thumbnail / hero image URL")
    published_at: datetime = Field(..., description="UTC publication timestamp")
    fetched_at: datetime = Field(..., description="UTC fetched timestamp")

    language: str = Field("en", description="Language code")
    region: str = Field("india", description="Geographic region")
    business_domain: str = Field("retail", description="Business domain (grocery, retail, etc.)")
    category: Optional[str] = Field(None, description="Article category")
    subcategory: Optional[str] = Field(None, description="Article subcategory")

    content_type: str = Field("news", description="Content type")
    extraction_method: str = Field("rss", description="Extraction method used")
    status: str = Field("published", description="Status")


from backend.app.schemas.enrichment import ArticleEnrichmentRead


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    source_name: str
    source_domain: str
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    original_url: str
    canonical_url: str
    image_url: Optional[str] = None
    published_at: datetime
    fetched_at: datetime
    language: str
    region: str
    business_domain: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    content_type: str
    extraction_method: str
    status: str
    created_at: datetime
    enrichment: Optional[ArticleEnrichmentRead] = None


class ArticleFilter(BaseModel):
    business_domain: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None
    source_id: Optional[str] = None
    language: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    cursor: Optional[str] = None
