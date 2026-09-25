from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.execution_log import ExecutionLog

router = APIRouter(prefix="/activity", tags=["activity"])


class ExecutionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    action_id: str | None
    action_type: str
    entity_type: str | None
    entity_id: str | None
    provider: str | None
    status: str
    result: str | None
    error_category: str | None
    summary: str | None
    started_at: datetime
    finished_at: datetime | None


@router.get("", response_model=list[ExecutionLogOut])
async def list_activity(
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.user_sub == user["sub"])
        .order_by(ExecutionLog.started_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
