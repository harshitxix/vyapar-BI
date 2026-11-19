from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    normalized_title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    language: Mapped[str] = mapped_column(String(10), default="en")
    region: Mapped[str] = mapped_column(String(64), nullable=False, default="india", index=True)
    business_domain: Mapped[str] = mapped_column(String(64), nullable=False, default="retail", index=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    content_type: Mapped[str] = mapped_column(String(32), default="news")
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False)  # rss, api, html, playwright
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    source: Mapped["Source"] = relationship("Source", back_populates="articles")
    enrichment: Mapped[Optional["ArticleEnrichment"]] = relationship(
        "ArticleEnrichment", back_populates="article", uselist=False, cascade="all, delete-orphan"
    )
    embedding: Mapped[Optional["ArticleEmbedding"]] = relationship(
        "ArticleEmbedding", back_populates="article", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_articles_domain_region_published", "business_domain", "region", "published_at"),
    )
