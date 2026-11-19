from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base


class ArticleEnrichment(Base):
    __tablename__ = "article_enrichment"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    article_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("articles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    secondary_domains: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    article_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    topics: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    keywords: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    entities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    events: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    article: Mapped["Article"] = relationship("Article", back_populates="enrichment")

    __table_args__ = (
        Index("ix_article_enrichment_status_attempts", "status", "attempt_count"),
    )
