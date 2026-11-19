from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MarketProfileBase(BaseModel):
    business_name: Optional[str] = None
    business_domain: str = "grocery"
    business_subdomain: Optional[str] = None
    business_description: Optional[str] = None
    country: str = "India"
    state: Optional[str] = None
    city: Optional[str] = None
    preferred_language: str = "en"


class MarketProfileCreate(MarketProfileBase):
    pass


class MarketProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    business_domain: Optional[str] = None
    business_subdomain: Optional[str] = None
    business_description: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    preferred_language: Optional[str] = None


class MarketProfileResponse(MarketProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TopicInterestCreate(BaseModel):
    topic: str
    preference_source: str = "manual"
    preference_score: float = 1.0


class TopicInterestResponse(BaseModel):
    id: str
    user_id: str
    topic_id: str
    preference_source: str
    preference_score: float
    is_explicit: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CanonicalEntityResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    aliases: Optional[List[str]] = None
    domain: Optional[str] = None
    is_followed: Optional[bool] = False

    class Config:
        from_attributes = True


class FollowEntityRequest(BaseModel):
    entity_id: str


class FeedPreferencesUpdate(BaseModel):
    freshness_bias: Optional[float] = None
    trend_bias: Optional[float] = None
    geographic_bias: Optional[float] = None
    followed_entities_bias: Optional[float] = None
    behavioural_personalization_enabled: Optional[bool] = None


class FeedPreferencesResponse(BaseModel):
    settings: Dict[str, Any]


class InteractionEventCreate(BaseModel):
    event_type: str
    article_id: Optional[str] = None
    trend_id: Optional[str] = None
    topic_id: Optional[str] = None
    entity_id: Optional[str] = None
    session_id: Optional[str] = None
    source_screen: str = "for_you"


class InteractionEventResponse(BaseModel):
    id: str
    status: str = "recorded"
    event_type: str
    timestamp: datetime


class PersonalizedItem(BaseModel):
    type: str  # 'article' or 'trend'
    id: str
    title: str
    description: Optional[str] = None
    relevance_score: Optional[float] = None
    personalization: Dict[str, Any]


class PersonalizedFeedResponse(BaseModel):
    status: str
    count: int
    total_candidates: Optional[int] = None
    has_more: bool
    next_cursor: Optional[str] = None
    items: List[Dict[str, Any]]
    diagnostics: Optional[Dict[str, Any]] = None

