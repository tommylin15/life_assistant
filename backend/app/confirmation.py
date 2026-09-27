from __future__ import annotations

import secrets
from urllib.parse import unquote

CONFIRMATION_HEADER = "X-Life-Assistant-Confirmation"
CALENDAR_DELETE_PATH_PREFIX = "/api/v1/integrations/google/calendar/events/"


def explicit_confirmation_value(action_type: str, target_id: str) -> str:
    """Return the exact per-action, per-target explicit-user confirmation value."""

    return f"explicit_user:{action_type}:{target_id}"


def confirmation_requirement(method: str, path: str) -> tuple[str, str] | None:
    """Return the destructive action/target that requires explicit confirmation."""

    if method.upper() != "DELETE" or not path.startswith(CALENDAR_DELETE_PATH_PREFIX):
        return None
    target_id = unquote(path[len(CALENDAR_DELETE_PATH_PREFIX) :]).strip()
    if not target_id:
        return None
    return ("calendar.delete", target_id)


def confirmation_satisfied(method: str, path: str, header_value: str | None) -> bool:
    requirement = confirmation_requirement(method, path)
    if requirement is None:
        return True
    action_type, target_id = requirement
    expected = explicit_confirmation_value(action_type, target_id)
    return secrets.compare_digest(header_value or "", expected)
