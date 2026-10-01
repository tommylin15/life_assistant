import secrets
from urllib.parse import unquote

CONFIRMATION_HEADER = "X-Life-Assistant-Confirmation"
CALENDAR_DELETE_PATH_PREFIX = "/api/v1/integrations/google/calendar/events/"
PROJECT_DELETE_PATH_PREFIX = "/api/v1/projects/"
NOTE_DELETE_PATH_PREFIX = "/api/v1/notes/"
DRIVE_WORKSPACE_DELETE_PATH_PREFIX = "/api/v1/drive/workspaces/"

_DESTRUCTIVE_DELETE_RULES = (
    (CALENDAR_DELETE_PATH_PREFIX, "calendar.delete"),
    (PROJECT_DELETE_PATH_PREFIX, "project.delete"),
    (NOTE_DELETE_PATH_PREFIX, "note.delete"),
    (DRIVE_WORKSPACE_DELETE_PATH_PREFIX, "drive.workspace.delete"),
)


def explicit_confirmation_value(action_type: str, target_id: str) -> str:
    """Return the exact per-action, per-target explicit-user confirmation value."""

    return f"explicit_user:{action_type}:{target_id}"


def _single_path_target(path: str, prefix: str) -> str | None:
    if not path.startswith(prefix):
        return None
    target_id = unquote(path[len(prefix) :]).strip()
    if not target_id or "/" in target_id:
        return None
    return target_id


def confirmation_requirement(method: str, path: str) -> tuple[str, str] | None:
    """Return the destructive action/target that requires explicit confirmation."""

    if method.upper() != "DELETE":
        return None
    for prefix, action_type in _DESTRUCTIVE_DELETE_RULES:
        target_id = _single_path_target(path, prefix)
        if target_id is not None:
            return (action_type, target_id)
    return None


def confirmation_satisfied(method: str, path: str, header_value: str | None) -> bool:
    requirement = confirmation_requirement(method, path)
    if requirement is None:
        return True
    action_type, target_id = requirement
    expected = explicit_confirmation_value(action_type, target_id)
    return secrets.compare_digest(header_value or "", expected)
