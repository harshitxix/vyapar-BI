from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.app.database.session import get_db
from backend.app.scheduler.manager import scheduler_manager

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unhealthy"
    try:
        result = await db.execute(text("SELECT 1;"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    scheduler_running = scheduler_manager._is_running if hasattr(scheduler_manager, "_is_running") else False

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "scheduler_active": scheduler_running,
    }
