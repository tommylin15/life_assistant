"""Add independent curated pool, rollout, personal UI and platform AI policy.

Revision ID: 20261010_0015
Revises: 20261009_0014
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261010_0015"
down_revision: str | None = "20261009_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "curated_activities",
        sa.Column("identity_key", sa.String(64), primary_key=True),
        sa.Column("occurrence_key", sa.String(80), nullable=False),
        sa.Column("title", sa.String(400), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("summary", sa.String(1200)),
        sa.Column("city", sa.String(100)),
        sa.Column("category", sa.String(100)),
        sa.Column("starts_on", sa.Date()),
        sa.Column("ends_on", sa.Date()),
        sa.Column("fee_kind", sa.String(24), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2)),
        sa.Column("benefit_value", sa.Numeric(12, 2)),
        sa.Column("on_site_spending", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("registration_required", sa.Boolean()),
        sa.Column("registration_status", sa.String(24), nullable=False),
        sa.Column("limited_offer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("registration_deadline", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("importance BETWEEN 1 AND 5", name="ck_curated_importance"),
        sa.CheckConstraint("fee_kind IN ('free','paid','conditional_free','unknown')", name="ck_curated_fee_kind"),
        sa.CheckConstraint("registration_status IN ('unknown','upcoming','open','full','closed')", name="ck_curated_registration"),
        sa.CheckConstraint("fee_amount IS NULL OR fee_amount >= 0", name="ck_curated_fee_amount"),
        sa.CheckConstraint("benefit_value IS NULL OR benefit_value >= 0", name="ck_curated_benefit"),
        sa.CheckConstraint("starts_on IS NULL OR ends_on IS NULL OR ends_on >= starts_on", name="ck_curated_dates"),
    )
    op.create_index("ix_curated_activity_date", "curated_activities", ["starts_on"])
    op.create_index("ix_curated_activity_city", "curated_activities", ["city"])
    op.create_table(
        "feature_rollouts",
        sa.Column("feature_key", sa.String(60), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("audience", sa.String(20), nullable=False, server_default="all"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('hidden','beta','enabled','maintenance')", name="ck_feature_rollout_status"),
        sa.CheckConstraint("audience IN ('all','owner')", name="ck_feature_rollout_audience"),
    )
    op.create_table(
        "user_ui_preferences",
        sa.Column("user_sub", sa.String(255), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nav_mode", sa.String(12), nullable=False, server_default="auto"),
        sa.Column("pinned", sa.JSON(), nullable=False),
        sa.Column("more_order", sa.JSON(), nullable=False),
        sa.Column("home_cards", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("nav_mode IN ('auto','bottom','sidebar')", name="ck_ui_nav_mode"),
    )
    op.create_table(
        "life_ai_policy",
        sa.Column("policy_key", sa.String(32), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allowed_providers", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Intentional fail-closed: deleting production curated data or preferences is prohibited.
    raise RuntimeError("No destructive downgrade for 0015")
