import asyncio

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def check_database() -> None:
    """Verify that the configured database accepts a simple query."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def database_target_kind() -> str:
    """Return a non-sensitive target category for readiness diagnostics."""
    host = (make_url(settings.database_url).host or "").lower()
    if host in {"", "localhost", "127.0.0.1", "::1"}:
        return "local"
    return "remote"


def database_error_kind(exc: Exception) -> str:
    """Classify a DB failure without exposing connection details or credentials."""
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"

    names: set[str] = set()
    pending: list[BaseException] = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        names.add(type(current).__name__.lower())
        for related in (
            getattr(current, "orig", None),
            getattr(current, "__cause__", None),
            getattr(current, "__context__", None),
        ):
            if isinstance(related, BaseException):
                pending.append(related)

    joined = " ".join(names)
    if "timeout" in joined:
        return "timeout"
    if any(token in joined for token in ("invalidpassword", "invalidauthorization", "authentication")):
        return "authentication"
    if any(token in joined for token in ("invalidcatalog", "undefineddatabase")):
        return "database_config"
    if any(token in joined for token in ("connectionrefused", "connectcall", "oserror", "operationalerror")):
        return "connection"
    return "database_error"
