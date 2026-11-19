from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.personalization import User
from backend.app.api.auth import get_current_user
from backend.app.schemas.personalization import (
    MarketProfileCreate,
    MarketProfileUpdate,
    MarketProfileResponse,
    TopicInterestCreate,
    TopicInterestResponse,
    CanonicalEntityResponse,
    FollowEntityRequest,
    FeedPreferencesUpdate,
    FeedPreferencesResponse,
)
from backend.app.services.personalization.user_service import UserProfileService
from backend.app.services.personalization.entity_service import EntityFollowService
from backend.app.services.personalization.taxonomy import TaxonomyService

router = APIRouter(prefix="/users/me", tags=["User Personalization"])
taxonomy_router = APIRouter(prefix="", tags=["Taxonomy & Entities"])


# ==========================================
# Market Profile Endpoints
# ==========================================

@router.get("/market-profile", response_model=Optional[MarketProfileResponse])
async def get_market_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves current user's market profile."""
    profile = await UserProfileService.get_profile(db, current_user.id)
    return profile


@router.post("/market-profile", response_model=MarketProfileResponse)
async def create_or_replace_market_profile(
    payload: MarketProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates or replaces the market profile for the current user."""
    profile = await UserProfileService.upsert_profile(
        db, current_user.id, payload.model_dump()
    )
    return profile


@router.patch("/market-profile", response_model=MarketProfileResponse)
async def update_market_profile(
    payload: MarketProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially updates current user's market profile."""
    clean_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    profile = await UserProfileService.upsert_profile(db, current_user.id, clean_data)
    return profile


# ==========================================
# Topic Interests Endpoints
# ==========================================

@router.get("/interests", response_model=List[TopicInterestResponse])
async def list_user_interests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists topics followed by the user."""
    interests = await UserProfileService.get_interests(db, current_user.id)
    return interests


@router.post("/interests", response_model=TopicInterestResponse)
async def add_user_interest(
    payload: TopicInterestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds a new topic of interest."""
    interest = await UserProfileService.add_interest(
        db,
        user_id=current_user.id,
        topic=payload.topic,
        preference_source=payload.preference_source,
        score=payload.preference_score,
    )
    return interest


@router.delete("/interests/{topic_id}")
async def remove_user_interest(
    topic_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes a topic of interest."""
    removed = await UserProfileService.remove_interest(db, current_user.id, topic_id)
    return {"status": "success", "removed": removed, "topic_id": topic_id}


# ==========================================
# Followed Entities Endpoints
# ==========================================

@router.get("/followed-entities", response_model=List[CanonicalEntityResponse])
async def list_followed_entities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists companies and brands followed by the user."""
    entities = await EntityFollowService.get_user_followed_entities(db, current_user.id)
    return [
        CanonicalEntityResponse(
            id=e.id,
            name=e.name,
            entity_type=e.entity_type,
            aliases=e.aliases,
            domain=e.domain,
            is_followed=True,
        )
        for e in entities
    ]


@router.post("/followed-entities", response_model=CanonicalEntityResponse)
async def follow_entity(
    payload: FollowEntityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Follows a canonical entity."""
    await EntityFollowService.follow_entity(db, current_user.id, payload.entity_id)
    entities = await EntityFollowService.get_user_followed_entities(db, current_user.id)
    target = next((e for e in entities if e.id == payload.entity_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Entity not found")
    return CanonicalEntityResponse(
        id=target.id,
        name=target.name,
        entity_type=target.entity_type,
        aliases=target.aliases,
        domain=target.domain,
        is_followed=True,
    )


@router.delete("/followed-entities/{entity_id}")
async def unfollow_entity(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unfollows a canonical entity."""
    removed = await EntityFollowService.unfollow_entity(db, current_user.id, entity_id)
    return {"status": "success", "unfollowed": removed, "entity_id": entity_id}


# ==========================================
# Feed Preferences & Privacy Endpoints
# ==========================================

@router.get("/feed-preferences", response_model=FeedPreferencesResponse)
async def get_feed_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves user feed tuning preferences and privacy toggles."""
    settings = await UserProfileService.get_feed_preferences(db, current_user.id)
    return FeedPreferencesResponse(settings=settings)


@router.patch("/feed-preferences", response_model=FeedPreferencesResponse)
async def update_feed_preferences(
    payload: FeedPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates user feed preferences."""
    clean_settings = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = await UserProfileService.update_feed_preferences(
        db, current_user.id, clean_settings
    )
    return FeedPreferencesResponse(settings=updated)


@router.post("/preferences/reset")
async def reset_learned_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resets all learned behavioural interaction preferences without deleting
    explicit onboarding profile selections.
    """
    count = await UserProfileService.reset_learned_preferences(db, current_user.id)
    return {"status": "success", "reset_learned_records": count}


# ==========================================
# Taxonomy & Canonical Entities Discovery
# ==========================================

@taxonomy_router.get("/taxonomy/domains")
async def get_domain_taxonomy():
    """Lists supported business domains, subdomains, and suggested topics."""
    return {"status": "success", "domains": TaxonomyService.get_supported_domains()}


@taxonomy_router.get("/entities", response_model=List[CanonicalEntityResponse])
async def list_entities(
    domain: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists suggested companies/brands available to follow."""
    all_entities = await EntityFollowService.list_canonical_entities(db, domain=domain)
    followed = await EntityFollowService.get_user_followed_entities(db, current_user.id)
    followed_ids = {e.id for e in followed}

    return [
        CanonicalEntityResponse(
            id=e.id,
            name=e.name,
            entity_type=e.entity_type,
            aliases=e.aliases,
            domain=e.domain,
            is_followed=e.id in followed_ids,
        )
        for e in all_entities
    ]
