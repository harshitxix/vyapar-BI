from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)  # scheduled, manual
    status: Mapped[str] = mapped_column(String(32), default="running")  # running, completed, failed
    
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    sources_attempted: Mapped[int] = mapped_column(Integer, default=0)
    sources_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    sources_failed: Mapped[int] = mapped_column(Integer, default=0)

    articles_discovered: Mapped[int] = mapped_column(Integer, default=0)
    articles_inserted: Mapped[int] = mapped_column(Integer, default=0)
    articles_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    articles_rejected: Mapped[int] = mapped_column(Integer, default=0)

    error_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
