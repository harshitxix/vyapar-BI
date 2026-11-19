import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None
    PGVECTOR_AVAILABLE = False

from backend.app.models.base import Base


class ArticleEmbedding(Base):
    """
    Stores vector embeddings and metadata for enriched articles.
    """
    __tablename__ = "article_embeddings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    article_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("articles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=384, nullable=False)
    embedding = mapped_column(JSONB, nullable=True)
    embedding_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    article: Mapped["Article"] = relationship("Article", back_populates="embedding")


class Trend(Base):
    """
    Canonical Market Trend object detected and scored by the Trend Engine.
    """
    __tablename__ = "trends"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    why_emerging: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_developments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="all")
    region: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="all")
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="Consumer Trend")
    
    # Lifecycle status: emerging, growing, established, cooling, declining, inactive
    status: Mapped[str] = mapped_column(String(32), default="emerging", nullable=False, index=True)
    
    # Evidence grade: high, medium, low
    evidence_grade: Mapped[str] = mapped_column(String(16), default="medium", nullable=False, index=True)
    
    # Deterministic scores (0.0 to 1.0 or -1.0 to 1.0)
    strength_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    coherence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    diversity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Metrics
    article_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    
    # Representative facets
    representative_topics: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    representative_entities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    trend_articles: Mapped[List["TrendArticle"]] = relationship(
        "TrendArticle", back_populates="trend", cascade="all, delete-orphan"
    )
    snapshots: Mapped[List["TrendSnapshot"]] = relationship(
        "TrendSnapshot", back_populates="trend", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_trends_domain_status_strength", "domain", "status", "strength_score"),
        Index("ix_trends_region_domain", "region", "domain"),
    )


class TrendArticle(Base):
    """
    Supporting evidence link connecting an article to a trend.
    """
    __tablename__ = "trend_articles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=1.0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    trend: Mapped["Trend"] = relationship("Trend", back_populates="trend_articles")
    article: Mapped["Article"] = relationship("Article")

    __table_args__ = (
        Index("ix_trend_articles_trend_article", "trend_id", "article_id", unique=True),
    )


class TrendSnapshot(Base):
    """
    Historical snapshot of a trend's state over time for timeline visualization.
    """
    __tablename__ = "trend_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    strength_score: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="emerging")

    trend: Mapped["Trend"] = relationship("Trend", back_populates="snapshots")


class TrendAnalysisRun(Base):
    """
    Audit log for batch trend detection runs.
    """
    __tablename__ = "trend_analysis_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    window_days: Mapped[int] = mapped_column(Integer, default=14)
    
    articles_considered: Mapped[int] = mapped_column(Integer, default=0)
    candidate_clusters: Mapped[int] = mapped_column(Integer, default=0)
    valid_trends: Mapped[int] = mapped_column(Integer, default=0)
    new_trends: Mapped[int] = mapped_column(Integer, default=0)
    updated_trends: Mapped[int] = mapped_column(Integer, default=0)
    discarded_clusters: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(32), default="running")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
