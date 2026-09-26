import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config as app_config
from app.api.activity import router as activity_router
from app.api.auth import router as auth_router
from app.api.google_integrations import router as google_integrations_router
from app.api.google_project import router as google_project_router
from app.api.habits import router as habits_router
from app.api.notes import router as notes_router
from app.api.projects import router as projects_router
from app.api.shopping import router as shopping_router
from app.api.tasks import router as tasks_router
from app.db import session as db_session
from app.db.session import Base, engine
from app.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    normalize_request_id,
    reset_request_id,
    set_request_id,
    unhandled_exception_handler,
    validation_exception_handler,
)

app = FastAPI(title="Life Assistant API", version="0.1.0", debug=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = normalize_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        reset_request_id(token)


app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.on_event("startup")
async def startup():
    try:
        # Transitional safety net for additive tables. Schema changes remain
        # versioned with Alembic and CI validates the migration chain.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logging.error(
            "DB startup error type=%s category=%s",
            type(exc).__name__,
            db_session.database_error_kind(exc),
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    try:
        await asyncio.wait_for(db_session.check_database(), timeout=5)
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unavailable",
                "diagnostic": {
                    "target": db_session.database_target_kind(),
                    "error": db_session.database_error_kind(exc),
                    "bundle_format": app_config.BUNDLE_FORMAT,
                    "bundle_shape": app_config.BUNDLE_SHAPE,
                    "bundle_password_key_hints": app_config.BUNDLE_PASSWORD_KEY_HINTS,
                    "bundle_key_hints": app_config.BUNDLE_KEY_HINTS,
                },
            },
        )
    return {"status": "ok", "database": "ok"}


app.include_router(auth_router)
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(notes_router, prefix="/api/v1")
app.include_router(habits_router, prefix="/api/v1")
app.include_router(shopping_router, prefix="/api/v1")
app.include_router(google_integrations_router, prefix="/api/v1")
app.include_router(google_project_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")
