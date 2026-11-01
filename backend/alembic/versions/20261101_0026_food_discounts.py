"""Add independent food_discounts table for Taipei/New Taipei 41-district food offers."""
from alembic import op
import sqlalchemy as sa

revision = "20261101_0026"
down_revision = "20261030_0025"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "food_discounts",
        sa.Column("candidate_key", sa.String(200), primary_key=True),
        sa.Column("city", sa.String(50)),
        sa.Column("district", sa.String(100)),
        sa.Column("merchant", sa.String(300), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("offer_summary", sa.String(1000), nullable=False),
        sa.Column("offer_type", sa.String(100)),
        sa.Column("nominal_discount", sa.String(120)),
        sa.Column("fixed_discount_ntd", sa.Numeric(10, 2)),
        sa.Column("original_price_ntd", sa.Numeric(10, 2)),
        sa.Column("offer_price_ntd", sa.Numeric(10, 2)),
        sa.Column("period_text", sa.String(400)),
        sa.Column("address", sa.String(600)),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("notes", sa.String(1200)),
        sa.Column("claim_status", sa.String(64), nullable=False, server_default="COLLECTED_SOURCE_CLAIM"),
        sa.Column("visibility_status", sa.String(64), nullable=False, server_default="VISIBLE_SOURCE_ONLY"),
        sa.Column("first_seen_on", sa.Date()),
        sa.Column("claim_deadline_on", sa.Date()),
        sa.Column("redemption_ends_on", sa.Date()),
        sa.Column("offer_ends_on", sa.Date()),
        sa.Column("last_positive_on", sa.Date()),
        sa.Column("next_refresh_on", sa.Date()),
        sa.Column("date_basis", sa.String(64)),
        sa.Column(
            "disclosure",
            sa.String(300),
            nullable=False,
            server_default="公開來源宣稱，未逐項核實，不保證到店可使用",
        ),
        sa.Column("details", sa.JSON()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_food_discounts_visibility", "food_discounts", ["visibility_status", "claim_status"])
    op.create_index("ix_food_discounts_city_district", "food_discounts", ["city", "district"])
    op.create_index("ix_food_discounts_category", "food_discounts", ["category"])


def downgrade():
    raise RuntimeError("Disable food_discounts by feature rollout; retain curated records for recovery")
