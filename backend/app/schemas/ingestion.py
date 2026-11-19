from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class IngestionTriggerRequest(BaseModel):
    source_id: Optional[str] = Field(None, description="Specific source to refresh, or null for all due/active")
    domain: Optional[str] = Field(None, description="Specific domain filter")


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    articles_discovered: int = 0
    articles_inserted: int = 0
    articles_duplicate: int = 0
    articles_rejected: int = 0
    error_details: Optional[Dict[str, Any]] = None
