import secrets
from urllib.parse import unquote

CONFIRMATION_HEADER = "X-Life-Assistant-Confirmation"
CALENDAR_DELETE_PATH_PREFIX = "/api/v1/integrations/google/calendar/events/"
PROJECT_DELETE_PATH_PREFIX = "/api/v1/projects/"
NOTE_DELETE_PATH_PREFIX = "/api/v1/notes/"
DRIVE_WORKSPACE_DELETE_PATH_PREFIX = "/api/v1/drive/workspaces/"
DRIVE_DOCUMENT_PATH_PREFIX = "/api/v1/drive/documents/"

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


def _drive_project_detach_target(path: str) -> str | None:
    if not path.startswith(DRIVE_DOCUMENT_PATH_PREFIX):
        return None
    remainder = path[len(DRIVE_DOCUMENT_PATH_PREFIX) :]
    parts = remainder.split("/")
    if len(parts) != 3 or parts[1] != "projects":
        return None
    document_id = unquote(parts[0]).strip()
    project_id = unquote(parts[2]).strip()
    if not document_id or not project_id or "/" in document_id or "/" in project_id:
        return None
    return f"{document_id}:{project_id}"


def confirmation_requirement(method: str, path: str) -> tuple[str, str] | None:
    """Return the destructive action/target that requires explicit confirmation."""

    if method.upper() != "DELETE":
        return None

    drive_project_target = _drive_project_detach_target(path)
    if drive_project_target is not None:
        return ("drive.document.project.detach", drive_project_target)

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
