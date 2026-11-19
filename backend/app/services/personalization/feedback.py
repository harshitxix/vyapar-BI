import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.article import Article
from backend.app.models.personalization import (
    UserInteractionEvent,
    UserLearnedPreference,
    UserFeedPreferences,
)
from backend.app.services.personalization.config import (
    PersonalizationConfig,
    DEFAULT_PERSONALIZATION_CONFIG,
)
from backend.app.services.personalization.taxonomy import TaxonomyService


class FeedbackService:
    """
    Ingests interaction events and maintains bounded, decaying learned preference scores.
    """

    @classmethod
    async def record_interaction(
        cls,
        db: AsyncSession,
        user_id: str,
        event_type: str,
        article_id: Optional[str] = None,
        trend_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_screen: str = "for_you",
        config: PersonalizationConfig = DEFAULT_PERSONALIZATION_CONFIG,
    ) -> UserInteractionEvent:
        """
        Records an interaction event and updates learned preferences accordingly.
        """
        event = UserInteractionEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            event_type=event_type,
            article_id=article_id,
            trend_id=trend_id,
            topic_id=TaxonomyService.normalize_topic(topic_id) if topic_id else None,
            entity_id=entity_id,
            session_id=session_id,
            source_screen=source_screen,
        )
        db.add(event)

        # Check if behavioural personalization is enabled for user
        feed_pref_res = await db.execute(
            select(UserFeedPreferences).where(UserFeedPreferences.user_id == user_id)
        )
        feed_pref = feed_pref_res.scalar_one_or_none()
        is_learning_enabled = (
            feed_pref.settings.get("behavioural_personalization_enabled", True)
            if feed_pref
            else True
        )

        delta = config.event_deltas.get(event_type, 0.0)

        if is_learning_enabled and delta != 0.0:
            targets_to_update: List[tuple[str, str]] = []  # (preference_type, target_id)

            # 1. Topic target
            if topic_id:
                targets_to_update.append(("topic", TaxonomyService.normalize_topic(topic_id)))

            # 2. Entity target
            if entity_id:
                targets_to_update.append(("entity", entity_id))

            # 3. Article targets
            if article_id:
                art_res = await db.execute(
                    select(Article)
                    .options(selectinload(Article.enrichment))
                    .where(Article.id == article_id)
                )
                article = art_res.scalar_one_or_none()
                if article:
                    enr = article.enrichment
                    domain = (enr.primary_domain if enr else None) or article.business_domain
                    if domain:
                        targets_to_update.append(("domain", domain.lower()))
                    if enr and enr.topics:
                        for t in enr.topics:
                            targets_to_update.append(("topic", TaxonomyService.normalize_topic(t)))
                    if enr and enr.entities:
                        for e in enr.entities:
                            ename = (e.get("name") if isinstance(e, dict) else str(e)).lower()
                            targets_to_update.append(("entity", ename))

            # Apply delta to learned preferences
            for pref_type, target_id in targets_to_update:
                if not target_id:
                    continue
                await cls._adjust_preference(db, user_id, pref_type, target_id, delta, config)

        await db.commit()
        await db.refresh(event)
        return event

    @classmethod
    async def _adjust_preference(
        cls,
        db: AsyncSession,
        user_id: str,
        preference_type: str,
        target_id: str,
        delta: float,
        config: PersonalizationConfig,
    ):
        """
        Updates or creates a learned preference score, bounding it to [0.0, 1.0].
        """
        res = await db.execute(
            select(UserLearnedPreference).where(
                UserLearnedPreference.user_id == user_id,
                UserLearnedPreference.preference_type == preference_type,
                UserLearnedPreference.target_id == target_id,
            )
        )
        pref = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if pref:
            # Apply time decay towards baseline (0.5) before adjusting
            age_days = max(0.0, (now - pref.last_interaction_at).total_seconds() / 86400.0)
            decay_factor = math.exp(-age_days / config.learned_preference_decay_days)
            decayed_score = 0.5 + (pref.preference_score - 0.5) * decay_factor

            new_score = max(
                config.min_preference_score,
                min(config.max_preference_score, decayed_score + delta),
            )
            pref.preference_score = round(new_score, 4)
            pref.evidence_count += 1
            pref.last_interaction_at = now
            pref.updated_at = now
        else:
            initial_score = max(
                config.min_preference_score,
                min(config.max_preference_score, 0.5 + delta),
            )
            pref = UserLearnedPreference(
                id=f"lrn_{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                preference_type=preference_type,
                target_id=target_id,
                preference_score=round(initial_score, 4),
                evidence_count=1,
                last_interaction_at=now,
                updated_at=now,
            )
            db.add(pref)

    @classmethod
    async def get_learned_preference_dict(
        cls, db: AsyncSession, user_id: str, config: PersonalizationConfig = DEFAULT_PERSONALIZATION_CONFIG
    ) -> Dict[str, float]:
        """
        Retrieves active learned preference scores decayed to current timestamp.
        Returns mapping: target_id -> decayed_score in [0.0, 1.0].
        """
        res = await db.execute(
            select(UserLearnedPreference).where(UserLearnedPreference.user_id == user_id)
        )
        prefs = res.scalars().all()
        now = datetime.now(timezone.utc)
        result: Dict[str, float] = {}

        for p in prefs:
            age_days = max(0.0, (now - p.last_interaction_at).total_seconds() / 86400.0)
            decay_factor = math.exp(-age_days / config.learned_preference_decay_days)
            decayed = 0.5 + (p.preference_score - 0.5) * decay_factor
            result[p.target_id] = round(decayed, 4)

        return result

