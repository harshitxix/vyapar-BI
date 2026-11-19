import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.personalization import (
    User,
    UserMarketProfile,
    UserTopicPreference,
    UserFeedPreferences,
    UserLearnedPreference,
)
from backend.app.services.personalization.taxonomy import TaxonomyService


class UserProfileService:
    """
    Manages user lifecycle, market profiles, topic interests, and feed preference settings.
    """

    @classmethod
    async def get_or_create_user(
        cls, db: AsyncSession, user_id: Optional[str] = None, email: Optional[str] = None
    ) -> User:
        """Finds or creates a user account."""
        if user_id:
            res = await db.execute(select(User).where(User.id == user_id))
            user = res.scalar_one_or_none()
            if user:
                return user

        if email:
            res = await db.execute(select(User).where(User.email == email))
            user = res.scalar_one_or_none()
            if user:
                return user

        new_user = User(
            id=user_id or f"usr_{uuid.uuid4().hex[:12]}",
            email=email,
            is_active=True,
        )
        db.add(new_user)
        # Initialize default feed preferences
        default_pref = UserFeedPreferences(
            id=f"pref_{uuid.uuid4().hex[:10]}",
            user_id=new_user.id,
            settings={
                "freshness_bias": 1.0,
                "trend_bias": 1.0,
                "geographic_bias": 1.0,
                "followed_entities_bias": 1.0,
                "behavioural_personalization_enabled": True,
            },
        )
        db.add(default_pref)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @classmethod
    async def get_profile(
        cls, db: AsyncSession, user_id: str
    ) -> Optional[UserMarketProfile]:
        """Gets user market profile."""
        res = await db.execute(
            select(UserMarketProfile).where(UserMarketProfile.user_id == user_id)
        )
        return res.scalar_one_or_none()

    @classmethod
    async def upsert_profile(
        cls, db: AsyncSession, user_id: str, profile_data: Dict[str, Any]
    ) -> UserMarketProfile:
        """Creates or updates a user market profile."""
        domain = profile_data.get("business_domain", "grocery")
        if not TaxonomyService.is_valid_domain(domain):
            domain = "grocery"

        subdomain = profile_data.get("business_subdomain")
        if subdomain and not TaxonomyService.is_valid_subdomain(domain, subdomain):
            subdomain = None

        res = await db.execute(
            select(UserMarketProfile).where(UserMarketProfile.user_id == user_id)
        )
        profile = res.scalar_one_or_none()

        if profile:
            profile.business_name = profile_data.get("business_name", profile.business_name)
            profile.business_domain = domain
            profile.business_subdomain = subdomain
            profile.business_description = profile_data.get(
                "business_description", profile.business_description
            )
            profile.country = profile_data.get("country", profile.country or "India")
            profile.state = profile_data.get("state", profile.state)
            profile.city = profile_data.get("city", profile.city)
            profile.preferred_language = profile_data.get(
                "preferred_language", profile.preferred_language or "en"
            )
            profile.updated_at = datetime.now(timezone.utc)
        else:
            profile = UserMarketProfile(
                id=f"prof_{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                business_name=profile_data.get("business_name"),
                business_domain=domain,
                business_subdomain=subdomain,
                business_description=profile_data.get("business_description"),
                country=profile_data.get("country", "India"),
                state=profile_data.get("state"),
                city=profile_data.get("city"),
                preferred_language=profile_data.get("preferred_language", "en"),
            )
            db.add(profile)

        await db.commit()
        await db.refresh(profile)
        return profile

    @classmethod
    async def get_interests(
        cls, db: AsyncSession, user_id: str
    ) -> List[UserTopicPreference]:
        """Lists user topic interests ordered by priority."""
        res = await db.execute(
            select(UserTopicPreference)
            .where(UserTopicPreference.user_id == user_id)
            .order_by(UserTopicPreference.preference_score.desc())
        )
        return list(res.scalars().all())

    @classmethod
    async def add_interest(
        cls,
        db: AsyncSession,
        user_id: str,
        topic: str,
        preference_source: str = "manual",
        score: float = 1.0,
    ) -> UserTopicPreference:
        """Adds or updates a topic interest."""
        clean_topic = TaxonomyService.normalize_topic(topic)
        if not clean_topic:
            raise ValueError("Topic cannot be empty")

        res = await db.execute(
            select(UserTopicPreference).where(
                UserTopicPreference.user_id == user_id,
                UserTopicPreference.topic_id == clean_topic,
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            existing.preference_source = preference_source
            existing.preference_score = max(0.0, min(1.0, score))
            existing.is_explicit = preference_source in ("onboarding", "manual")
            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)
            return existing

        new_interest = UserTopicPreference(
            id=f"top_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            topic_id=clean_topic,
            preference_source=preference_source,
            preference_score=max(0.0, min(1.0, score)),
            is_explicit=preference_source in ("onboarding", "manual"),
        )
        db.add(new_interest)
        await db.commit()
        await db.refresh(new_interest)
        return new_interest

    @classmethod
    async def remove_interest(
        cls, db: AsyncSession, user_id: str, topic_id: str
    ) -> bool:
        """Removes a topic interest."""
        clean_topic = TaxonomyService.normalize_topic(topic_id)
        res = await db.execute(
            delete(UserTopicPreference).where(
                UserTopicPreference.user_id == user_id,
                UserTopicPreference.topic_id == clean_topic,
            )
        )
        await db.commit()
        return res.rowcount > 0

    @classmethod
    async def get_feed_preferences(
        cls, db: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Gets user feed preference settings."""
        res = await db.execute(
            select(UserFeedPreferences).where(UserFeedPreferences.user_id == user_id)
        )
        pref = res.scalar_one_or_none()
        if pref:
            return pref.settings
        return {
            "freshness_bias": 1.0,
            "trend_bias": 1.0,
            "geographic_bias": 1.0,
            "followed_entities_bias": 1.0,
            "behavioural_personalization_enabled": True,
        }

    @classmethod
    async def update_feed_preferences(
        cls, db: AsyncSession, user_id: str, new_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Updates user feed preference settings."""
        res = await db.execute(
            select(UserFeedPreferences).where(UserFeedPreferences.user_id == user_id)
        )
        pref = res.scalar_one_or_none()
        if not pref:
            pref = UserFeedPreferences(
                id=f"pref_{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                settings=new_settings,
            )
            db.add(pref)
        else:
            merged = dict(pref.settings)
            merged.update(new_settings)
            pref.settings = merged
            pref.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(pref)
        return pref.settings

    @classmethod
    async def reset_learned_preferences(cls, db: AsyncSession, user_id: str) -> int:
        """
        Wipes all learned/inferred preference scores and resets to explicit selections only.
        """
        del_learned = await db.execute(
            delete(UserLearnedPreference).where(UserLearnedPreference.user_id == user_id)
        )
        del_inferred = await db.execute(
            delete(UserTopicPreference).where(
                UserTopicPreference.user_id == user_id,
                UserTopicPreference.is_explicit == False,
            )
        )
        await db.commit()
        return del_learned.rowcount + del_inferred.rowcount
