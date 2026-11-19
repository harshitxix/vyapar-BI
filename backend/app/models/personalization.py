import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base


class User(Base):
    """
    User entity representing registered or guest accounts.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    profile: Mapped[Optional["UserMarketProfile"]] = relationship(
        "UserMarketProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    feed_preferences: Mapped[Optional["UserFeedPreferences"]] = relationship(
        "UserFeedPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    topic_preferences: Mapped[List["UserTopicPreference"]] = relationship(
        "UserTopicPreference", back_populates="user", cascade="all, delete-orphan"
    )
    followed_entities: Mapped[List["UserEntityFollow"]] = relationship(
        "UserEntityFollow", back_populates="user", cascade="all, delete-orphan"
    )
    interaction_events: Mapped[List["UserInteractionEvent"]] = relationship(
        "UserInteractionEvent", back_populates="user", cascade="all, delete-orphan"
    )
    learned_preferences: Mapped[List["UserLearnedPreference"]] = relationship(
        "UserLearnedPreference", back_populates="user", cascade="all, delete-orphan"
    )


class UserMarketProfile(Base):
    """
    Structured market context that the user wants to monitor.
    """
    __tablename__ = "user_market_profiles"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    business_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    business_domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="grocery")
    business_subdomain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    business_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="India")
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")


class CanonicalEntity(Base):
    """
    Deduplicated registry of named companies, brands, and organizations.
    """
    __tablename__ = "canonical_entities"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPANY")
    aliases: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    followers: Mapped[List["UserEntityFollow"]] = relationship(
        "UserEntityFollow", back_populates="entity", cascade="all, delete-orphan"
    )


class UserEntityFollow(Base):
    """
    Many-to-many junction linking users to followed canonical entities.
    """
    __tablename__ = "user_entity_follows"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="followed_entities")
    entity: Mapped["CanonicalEntity"] = relationship("CanonicalEntity", back_populates="followers")

    __table_args__ = (
        UniqueConstraint("user_id", "entity_id", name="uq_user_entity_follow"),
    )


class UserTopicPreference(Base):
    """
    Structured topic interests selected or inferred for a user.
    """
    __tablename__ = "user_topic_preferences"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    preference_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"  # 'onboarding', 'manual', 'inferred'
    )
    preference_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_explicit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="topic_preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_preference"),
    )


class UserFeedPreferences(Base):
    """
    User-configurable feed tuning weights and personalization toggles.
    """
    __tablename__ = "user_feed_preferences"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "freshness_bias": 1.0,
            "trend_bias": 1.0,
            "geographic_bias": 1.0,
            "followed_entities_bias": 1.0,
            "behavioural_personalization_enabled": True,
        },
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="feed_preferences")


class UserInteractionEvent(Base):
    """
    Immutable audit stream recording user interactions with articles, trends, and topics.
    """
    __tablename__ = "user_interaction_events"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # article_view, article_open, article_save, article_dismiss, article_not_interested, trend_open, etc.
    article_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("articles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    trend_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("trends.id", ondelete="SET NULL"), nullable=True, index=True
    )
    topic_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("canonical_entities.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_screen: Mapped[str] = mapped_column(String(64), default="for_you", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="interaction_events")
    article: Mapped[Optional["Article"]] = relationship("Article")
    trend: Mapped[Optional["Trend"]] = relationship("Trend")
    entity: Mapped[Optional["CanonicalEntity"]] = relationship("CanonicalEntity")


class UserLearnedPreference(Base):
    """
    Aggregated and bounded preference scores updated gradually from interaction feedback.
    """
    __tablename__ = "user_learned_preferences"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    preference_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'topic', 'entity', 'domain', 'category'
    target_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    preference_score: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )  # Bounded strictly in [0.0, 1.0]
    evidence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="learned_preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "preference_type", "target_id", name="uq_user_learned_pref"),
        Index("ix_learned_pref_user_type_score", "user_id", "preference_type", "preference_score"),
    )
