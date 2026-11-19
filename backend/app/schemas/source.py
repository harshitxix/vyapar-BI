from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceBase(BaseModel):
    name: str = Field(..., description="Human-readable name of the source")
    domain: str = Field(..., description="Domain of the source")
    source_type: str = Field("rss", description="Source type: rss, api, html, playwright")
    base_url: str = Field(..., description="Base website URL")
    feed_url: Optional[str] = Field(None, description="RSS/Atom feed URL if applicable")
    api_endpoint: Optional[str] = Field(None, description="API endpoint URL if applicable")
    business_domains: List[str] = Field(default_factory=list, description="Target business domains")
    regions: List[str] = Field(default_factory=list, description="Target regions")
    language: str = Field("en", description="Language code")
    refresh_interval: int = Field(900, description="Polling refresh interval in seconds")
    priority: int = Field(1, description="Priority ranking")
    active: bool = Field(True, description="Whether source is actively polled")


class SourceCreate(SourceBase):
    id: str = Field(..., description="Unique source identifier")


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    source_type: Optional[str] = None
    base_url: Optional[str] = None
    feed_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    business_domains: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    language: Optional[str] = None
    refresh_interval: Optional[int] = None
    priority: Optional[int] = None
    active: Optional[bool] = None
    status: Optional[str] = None


class SourceResponse(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    last_response_time_ms: Optional[int] = None
    last_article_count: int = 0
    created_at: datetime
    updated_at: datetime
