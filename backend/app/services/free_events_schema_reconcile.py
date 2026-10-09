"""Fail-closed reconciliation of event tables precreated by legacy API startup.

Only adopted when the live PostgreSQL table matches the expected *current*
SQLAlchemy metadata, including columns, types, PK, FK, uniqueness, named CHECKs
and indexes. No drop, rename, stamp, ALTER or data rewrite is performed.
Used by additive 0011/0012/0013 on older production databases.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from app.db.session import Base
from app.models import free_events as _event_models  # noqa: F401


def _error(table: str, kind: str) -> None:
    raise RuntimeError(
        f"free_events_precreated_schema_mismatch table={table} kind={kind}"
    )


def assert_compatible_existing_table(name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(name):
        _error(name, "missing")
    expected = Base.metadata.tables.get(name)
    if expected is None:
        _error(name, "not_in_code_metadata")

    actual_columns = {col["name"]: col for col in inspector.get_columns(name)}
    expected_columns = {col.name: col for col in expected.columns}
    if set(actual_columns) != set(expected_columns):
        _error(name, "columns")
    dialect = bind.dialect
    for key, col in expected_columns.items():
        actual = actual_columns[key]
        want_type = col.type.compile(dialect=dialect).upper()
        got_type = actual["type"].compile(dialect=dialect).upper()
        if want_type != got_type:
            _error(name, "type:" + key)
        if bool(actual["nullable"]) != bool(col.nullable):
            _error(name, "nullability:" + key)
        if col.server_default is not None and actual["default"] is None:
            _error(name, "server_default:" + key)
    actual_pk = tuple(inspector.get_pk_constraint(name).get("constrained_columns") or ())
    expected_pk = tuple(c.name for c in expected.primary_key.columns)
    if actual_pk != expected_pk:
        _error(name, "primary_key")

    expected_unique = {
        frozenset(c.name for c in constraint.columns)
        for constraint in expected.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    actual_unique = {
        frozenset(row.get("column_names") or ())
        for row in inspector.get_unique_constraints(name)
    }
    if expected_unique != actual_unique:
        _error(name, "unique_constraints")

    expected_checks = {
        constraint.name for constraint in expected.constraints
        if isinstance(constraint, sa.CheckConstraint)
    }
    actual_checks = {
        row["name"] for row in inspector.get_check_constraints(name)
    }
    if expected_checks != actual_checks:
        _error(name, "check_constraints")

    expected_fk = {
        (tuple(c.name for c in constraint.columns),
         tuple(element.target_fullname for element in constraint.elements))
        for constraint in expected.constraints
        if isinstance(constraint, sa.ForeignKeyConstraint)
    }
    actual_fk = {
        (tuple(row.get("constrained_columns") or ()),
         tuple(f"{row['referred_table']}.{name}" for name in
               (row.get("referred_columns") or ())))
        for row in inspector.get_foreign_keys(name)
    }
    if expected_fk != actual_fk:
        _error(name, "foreign_keys")

    expected_indexes = {
        (idx.name, tuple(col.name for col in idx.columns), bool(idx.unique))
        for idx in expected.indexes
    }
    actual_indexes = {
        (idx["name"], tuple(idx.get("column_names") or ()), bool(idx.get("unique")))
        for idx in inspector.get_indexes(name)
        if not idx.get("duplicates_constraint")
    }
    if expected_indexes != actual_indexes:
        _error(name, "indexes")


def create_checked_table(name: str, *args, **kwargs) -> None:
    if sa.inspect(op.get_bind()).has_table(name):
        assert_compatible_existing_table(name)
        return
    op.create_table(name, *args, **kwargs)


def create_checked_index(name: str, table_name: str, columns, **kwargs) -> None:
    inspector = sa.inspect(op.get_bind())
    matches = [row for row in inspector.get_indexes(table_name)
               if row["name"] == name]
    if matches:
        if len(matches) != 1 or tuple(matches[0].get("column_names") or ()) != tuple(columns):
            _error(table_name, "index:" + name)
        return
    op.create_index(name, table_name, columns, **kwargs)
