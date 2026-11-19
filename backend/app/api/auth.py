import jwt
import logging
from typing import Optional
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.personalization import User
from backend.app.services.personalization.user_service import UserProfileService

logger = logging.getLogger(__name__)

JWT_SECRET = "vyapar_secret_key_phase4_personalization"
JWT_ALGORITHM = "HS256"


async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the current user context from either JWT Bearer token,
    X-User-ID header, or a fallback default user.
    """
    user_id: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub") or payload.get("user_id")
        except Exception as e:
            logger.warning(f"[AUTH] Failed to decode JWT token: {e}")

    if not user_id and x_user_id:
        user_id = x_user_id.strip()

    if not user_id:
        user_id = "usr_guest_default"

    user = await UserProfileService.get_or_create_user(db, user_id=user_id)
    return user


def create_access_token(user_id: str) -> str:
    """Creates a JWT access token for a given user ID."""
    payload = {"sub": user_id, "user_id": user_id}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

