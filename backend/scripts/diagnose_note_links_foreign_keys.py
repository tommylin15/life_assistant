#!/usr/bin/env python3
"""Read-only diagnosis for note_links foreign-key contract drift."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings
from scripts import apply_cloud_domain_parity_migration as migration
from scripts import preflight_alembic_metadata_bootstrap as metadata_preflight


EXPECTED_NOTE_LINKS_FKS = metadata_preflight.EXPECTED_FOREIGN_KEY_CONTRACTS[
    "note_links"
]
SOURCE_REFERENCE = ("source_note_id", "notes", "id")
TARGET_REFERENCE = ("target_note_id", "notes", "id")


class NoteLinksForeignKeyDiagnosisError(migration.MigrationContractError):
    """A stable, read-only reason for note_links FK drift."""

    VALID_REASONS = {
        "both_missing",
        "source_missing",
        "target_missing",
        "semantics_mismatch",
        "other",
    }

    def __init__(self, reason: str):
        if reason not in self.VALID_REASONS:
            raise ValueError(f"unknown note_links FK diagnosis reason: {reason}")
        self.reason = reason
        super().__init__(f"note_links foreign key diagnosis: {reason}")


def diagnose_note_links_foreign_keys(
    actual_contracts: set[tuple[str, str, str, str, str, bool, bool, bool]],
) -> str | None:
    """Return a stable mismatch subtype without mutating the database."""

    if actual_contracts == EXPECTED_NOTE_LINKS_FKS:
        return None

    if not actual_contracts:
        return "both_missing"

    actual_references = {
        (contract[0], contract[1], contract[2]) for contract in actual_contracts
    }
    expected_references = {SOURCE_REFERENCE, TARGET_REFERENCE}

    if actual_references == {TARGET_REFERENCE}:
        return "source_missing"
    if actual_references == {SOURCE_REFERENCE}:
        return "target_missing"
    if actual_references == expected_references:
        return "semantics_mismatch"
    return "other"


async def inspect_note_links_foreign_keys(conn: AsyncConnection) -> str | None:
    tables = await migration._public_tables(conn)
    if "alembic_version" in tables:
        return None

    if not migration.validate_unversioned_baseline_tables(tables):
        return None

    actual = await metadata_preflight._foreign_key_contracts(conn, "note_links")
    return diagnose_note_links_foreign_keys(actual)


async def run_diagnosis() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            reason = await inspect_note_links_foreign_keys(conn)
    finally:
        await engine.dispose()

    if reason is not None:
        raise NoteLinksForeignKeyDiagnosisError(reason)
