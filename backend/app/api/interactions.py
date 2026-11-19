from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.personalization import User
from backend.app.api.auth import get_current_user
from backend.app.schemas.personalization import (
    InteractionEventCreate,
    InteractionEventResponse,
)
from backend.app.services.personalization.feedback import FeedbackService

router = APIRouter(prefix="", tags=["User Interactions & Feedback"])


@router.post("/interactions", response_model=InteractionEventResponse)
async def record_user_interaction(
    payload: InteractionEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Records a user interaction (click, dwell, bookmark, share, dismiss, not_interested)
    and incrementally updates behavioral preference weights.
    """
    try:
        event = await FeedbackService.record_interaction(
            db=db,
            user_id=current_user.id,
            event_type=payload.event_type,
            article_id=payload.article_id,
            trend_id=payload.trend_id,
            topic_id=payload.topic_id,
            entity_id=payload.entity_id,
            session_id=payload.session_id,
            source_screen=payload.source_screen,
        )
        return InteractionEventResponse(
            id=event.id,
            status="recorded",
            event_type=event.event_type,
            timestamp=event.created_at,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record interaction: {str(exc)}",
        )
