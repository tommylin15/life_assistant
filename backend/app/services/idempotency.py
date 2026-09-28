import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ApiError, current_request_id
from app.models.execution_log import ExecutionLog
from app.services.execution_log import fail_execution, finish_execution, start_execution


ACTION_ID_HEADER = "X-Life-Assistant-Action-ID"
_ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
T = TypeVar("T")


@dataclass(slots=True)
class ExecutionReservation:
    execution: ExecutionLog
    is_replay: bool


def normalize_action_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not _ACTION_ID_PATTERN.fullmatch(normalized):
        raise ApiError(
            400,
            "invalid_action_id",
            "Action ID must be 1-128 characters using letters, numbers, '.', '_', ':', or '-'",
        )
    return normalized


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Unsupported idempotency payload value: {type(value).__name__}")


def request_fingerprint(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def reserve_execution(
    db: AsyncSession,
    *,
    user_sub: str,
    action_type: str,
    action_id: str | None,
    request_payload: Any,
    provider: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    summary: str | None = None,
) -> ExecutionReservation:
    normalized_action_id = normalize_action_id(action_id)
    if normalized_action_id is None:
        execution = await start_execution(
            db,
            user_sub=user_sub,
            action_type=action_type,
            provider=provider,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
        )
        return ExecutionReservation(execution=execution, is_replay=False)

    fingerprint = request_fingerprint(request_payload)
    execution = ExecutionLog(
        id=str(uuid.uuid4()),
        request_id=current_request_id(),
        action_id=normalized_action_id,
        request_hash=fingerprint,
        user_sub=user_sub,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        provider=provider,
        status="running",
        summary=summary,
    )
    db.add(execution)
    try:
        await db.commit()
        await db.refresh(execution)
        return ExecutionReservation(execution=execution, is_replay=False)
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(ExecutionLog).where(
                ExecutionLog.user_sub == user_sub,
                ExecutionLog.action_type == action_type,
                ExecutionLog.action_id == normalized_action_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise ApiError(
                503,
                "audit_unavailable",
                "Idempotency reservation could not be resolved",
            )
        if existing.request_hash != fingerprint:
            raise ApiError(
                409,
                "idempotency_conflict",
                "Action ID was already used with a different request",
            )
        if existing.status == "success":
            return ExecutionReservation(execution=existing, is_replay=True)
        if existing.status == "running":
            raise ApiError(
                409,
                "idempotency_in_progress",
                "Action with this ID is already in progress",
            )
        raise ApiError(
            409,
            "idempotency_previous_failure",
            "Action ID belongs to a previous failed execution; use a new Action ID",
        )
    except Exception as exc:
        await db.rollback()
        raise ApiError(
            503,
            "audit_unavailable",
            "Idempotency reservation is unavailable; action was not executed",
        ) from exc


async def replay_entity(
    db: AsyncSession,
    reservation: ExecutionReservation,
    model: type[T],
) -> T:
    if not reservation.is_replay:
        raise RuntimeError("replay_entity requires a replay reservation")
    entity_id = reservation.execution.entity_id
    if not entity_id:
        raise ApiError(
            409,
            "idempotency_result_unavailable",
            "The previous action completed but its result cannot be replayed",
        )
    entity = await db.get(model, entity_id)
    if entity is None:
        raise ApiError(
            409,
            "idempotency_result_unavailable",
            "The previous action result is no longer available",
        )
    return entity


async def commit_reserved_execution(
    db: AsyncSession,
    reservation: ExecutionReservation,
    *,
    result: str,
    entity_id: str | None = None,
    entity_type: str | None = None,
    summary: str | None = None,
    failure_summary: str,
    refresh_entity: Any | None = None,
) -> None:
    execution = reservation.execution
    if execution.action_id is None:
        try:
            await db.commit()
            if refresh_entity is not None:
                await db.refresh(refresh_entity)
        except Exception as exc:
            await fail_execution(db, execution, exc, summary=failure_summary)
            raise
        await finish_execution(
            db,
            execution,
            result=result,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
        )
        return

    try:
        # Flush and refresh before the final commit so the business row and the
        # successful idempotency/audit result become durable atomically.
        await db.flush()
        if refresh_entity is not None:
            await db.refresh(refresh_entity)
        execution.status = "success"
        execution.result = result
        execution.error_category = None
        if entity_type is not None:
            execution.entity_type = entity_type
        if entity_id is not None:
            execution.entity_id = entity_id
        if summary is not None:
            execution.summary = summary
        execution.finished_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary=failure_summary)
        raise
