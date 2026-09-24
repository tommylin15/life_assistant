import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
from app.db import session as db_session
from app.db.session import Base, engine

app = FastAPI(title="Life Assistant API", version="0.1.0", debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        import logging
        logging.error(f"DB startup error: {e}")


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
                },
            },
        )
    return {"status": "ok", "database": "ok"}


app.include_router(auth_router)
app.include_router(tasks_router, prefix="/api/v1")
