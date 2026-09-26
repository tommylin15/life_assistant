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
        "driver_action_representation",
        "source_update_action",
        "target_update_action",
        "both_update_action",
        "source_delete_action",
        "target_delete_action",
        "both_delete_action",
        "source_deferrable",
        "target_deferrable",
        "both_deferrable",
        "source_initially_deferred",
        "target_initially_deferred",
        "both_initially_deferred",
        "source_validation",
        "target_validation",
        "both_validation",
        "semantics_complex",
        "other",
    }

    def __init__(self, reason: str):
        if reason not in self.VALID_REASONS:
            raise ValueError(f"unknown note_links FK diagnosis reason: {reason}")
        self.reason = reason
        super().__init__(f"note_links foreign key diagnosis: {reason}")


def _by_reference(
    contracts: set[tuple[str, str, str, str, str, bool, bool, bool]],
) -> dict[tuple[str, str, str], tuple[str, str, str, str, str, bool, bool, bool]]:
    return {(c[0], c[1], c[2]): c for c in contracts}


def _driver_action_representation_only(
    actual_by_ref: dict[
        tuple[str, str, str], tuple[str, str, str, str, str, bool, bool, bool]
    ],
    expected_by_ref: dict[
        tuple[str, str, str], tuple[str, str, str, str, str, bool, bool, bool]
    ],
) -> bool:
    """Detect async driver byte-string rendering of pg_catalog internal \"char\"."""

    saw_representation_difference = False
    for reference, expected in expected_by_ref.items():
        actual = actual_by_ref[reference]
        # Non-action semantics must already be exact.
        if actual[5:] != expected[5:]:
            return False
        for actual_action, expected_action in zip(actual[3:5], expected[3:5], strict=True):
            if actual_action == expected_action:
                continue
            if actual_action == f"b'{expected_action}'":
                saw_representation_difference = True
                continue
            return False
    return saw_representation_difference


def _single_semantic_field_reason(
    actual_by_ref: dict[
        tuple[str, str, str], tuple[str, str, str, str, str, bool, bool, bool]
    ],
    expected_by_ref: dict[
        tuple[str, str, str], tuple[str, str, str, str, str, bool, bool, bool]
    ],
) -> str | None:
    fields = (
        (3, "update_action"),
        (4, "delete_action"),
        (5, "deferrable"),
        (6, "initially_deferred"),
        (7, "validation"),
    )
    differing: list[tuple[int, str, set[str]]] = []
    for index, label in fields:
        scopes: set[str] = set()
        for scope, reference in (
            ("source", SOURCE_REFERENCE),
            ("target", TARGET_REFERENCE),
        ):
            if actual_by_ref[reference][index] != expected_by_ref[reference][index]:
                scopes.add(scope)
        if scopes:
            differing.append((index, label, scopes))

    if len(differing) != 1:
        return None

    _, label, scopes = differing[0]
    if scopes == {"source", "target"}:
        scope = "both"
    elif scopes == {"source"}:
        scope = "source"
    elif scopes == {"target"}:
        scope = "target"
    else:  # defensive: unreachable with fixed source/target loop
        return None
    return f"{scope}_{label}"


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
    if actual_references != expected_references:
        return "other"

    actual_by_ref = _by_reference(actual_contracts)
    expected_by_ref = _by_reference(EXPECTED_NOTE_LINKS_FKS)
    if _driver_action_representation_only(actual_by_ref, expected_by_ref):
        return "driver_action_representation"

    single_reason = _single_semantic_field_reason(actual_by_ref, expected_by_ref)
    if single_reason is not None:
        return single_reason
    return "semantics_complex"


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
