from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class SupportingArticleItem(BaseModel):
    id: str
    title: str
    source_name: str
    published_at: datetime
    original_url: str
    image_url: Optional[str] = None
    similarity_score: float = 1.0


class TrendSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    domain: str
    region: str
    category: str
    status: str
    evidence_grade: str
    strength_score: float
    confidence_score: float
    momentum_score: float
    article_count: int
    source_count: int
    first_detected_at: datetime
    last_updated_at: datetime
    representative_topics: List[str] = Field(default_factory=list)


class TrendDetailResponse(TrendSummaryResponse):
    why_emerging: Optional[str] = None
    key_developments: List[str] = Field(default_factory=list)
    coherence_score: float = 0.0
    diversity_score: float = 0.0
    representative_entities: List[str] = Field(default_factory=list)
    supporting_articles: List[SupportingArticleItem] = Field(default_factory=list)


class TrendSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    article_count: int
    source_count: int
    strength_score: float
    momentum_score: float
    status: str


class TrendAnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    domain: Optional[str] = None
    region: Optional[str] = None
    window_days: int
    articles_considered: int
    candidate_clusters: int
    valid_trends: int
    new_trends: int
    updated_trends: int
    discarded_clusters: int
    duration_ms: int
    status: str
    error_message: Optional[str] = None


class TrendRebuildRequest(BaseModel):
    domain: Optional[str] = None
    region: Optional[str] = "india"
    window_days: int = 14
    baseline_days: int = 45
