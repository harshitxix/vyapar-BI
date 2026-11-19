from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # rss, api, html, playwright
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    feed_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_endpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    business_domains: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    regions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    language: Mapped[str] = mapped_column(String(10), default="en")
    
    refresh_interval: Mapped[int] = mapped_column(Integer, default=900)  # seconds
    priority: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="healthy")  # healthy, degraded, failed, inactive
    
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_article_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    articles: Mapped[List["Article"]] = relationship("Article", back_populates="source", cascade="all, delete-orphan")
