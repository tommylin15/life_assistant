import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ApiError, current_request_id, error_code_from_exception
from app.models.execution_log import ExecutionLog


async def start_execution(
    db: AsyncSession,
    *,
    user_sub: str,
    action_type: str,
    provider: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action_id: str | None = None,
    summary: str | None = None,
) -> ExecutionLog:
    log = ExecutionLog(
        id=str(uuid.uuid4()),
        request_id=current_request_id(),
        action_id=action_id,
        user_sub=user_sub,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        provider=provider,
        status="running",
        summary=summary,
    )
    db.add(log)
    try:
        await db.commit()
        await db.refresh(log)
    except Exception as exc:
        await db.rollback()
        raise ApiError(
            503,
            "audit_unavailable",
            "Audit logging is unavailable; action was not executed",
        ) from exc
    return log


async def finish_execution(
    db: AsyncSession,
    log: ExecutionLog,
    *,
    status: str = "success",
    result: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    summary: str | None = None,
    error_category: str | None = None,
) -> None:
    log.status = status
    log.result = result
    log.error_category = error_category
    if entity_type is not None:
        log.entity_type = entity_type
    if entity_id is not None:
        log.entity_id = entity_id
    if summary is not None:
        log.summary = summary
    log.finished_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise ApiError(
            500,
            "audit_finalize_failed",
            "Action may have completed but audit finalization failed",
        ) from exc


async def fail_execution(
    db: AsyncSession,
    log: ExecutionLog,
    exc: Exception,
    *,
    status: str = "failure",
    summary: str | None = None,
) -> None:
    await db.rollback()
    log.status = status
    log.result = None
    log.error_category = error_code_from_exception(exc)
    if summary is not None:
        log.summary = summary
    log.finished_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except Exception as audit_exc:
        await db.rollback()
        raise ApiError(
            500,
            "audit_failure_record_failed",
            "Action failed and audit recording also failed",
        ) from audit_exc
