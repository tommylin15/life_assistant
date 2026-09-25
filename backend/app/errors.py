import logging
import re
import uuid
from contextvars import ContextVar, Token

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def normalize_request_id(value: str | None) -> str:
    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


def set_request_id(value: str) -> Token:
    return _request_id.set(value)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def current_request_id() -> str:
    return _request_id.get() or str(uuid.uuid4())


def request_id_from_request(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if isinstance(value, str) and value:
        return value
    return current_request_id()


def error_code_from_exception(exc: Exception) -> str:
    if isinstance(exc, ApiError):
        return exc.code
    if isinstance(exc, StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code")
            if isinstance(code, str) and code:
                return code
        return f"http_{exc.status_code}"
    return "internal_error"


def _http_message(exc: StarletteHTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message:
            return message
    if exc.status_code >= 500:
        return "Request failed"
    if isinstance(detail, str) and detail:
        return detail
    return "Request failed"


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = request_id_from_request(request)
    response = JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _error_response(
        request,
        exc.status_code,
        exc.code,
        exc.message,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return _error_response(
        request,
        exc.status_code,
        error_code_from_exception(exc),
        _http_message(exc),
    )


async def validation_exception_handler(
    request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        request,
        422,
        "validation_error",
        "Request validation failed",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_from_request(request)
    logger.error(
        "Unhandled request error request_id=%s type=%s",
        request_id,
        type(exc).__name__,
    )
    return _error_response(
        request,
        500,
        "internal_error",
        "Internal server error",
    )
