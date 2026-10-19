"""Add bounded, versioned Gmail V2 classification evidence (no email body).

Revision ID: 20261019_0022
Revises: 20261017_0021
"""
from alembic import op
import sqlalchemy as sa

revision = "20261019_0022"
down_revision = "20261017_0021"
branch_labels = depends_on = None


def upgrade():
    op.add_column("gmail_radar_seen", sa.Column(
        "classifier_version", sa.String(32), nullable=False, server_default="legacy-v1"))
    op.add_column("gmail_radar_items", sa.Column(
        "classifier_version", sa.String(32), nullable=False, server_default="legacy-v1"))
    op.add_column("gmail_radar_items", sa.Column(
        "classification_source", sa.String(24), nullable=False, server_default="rules"))
    op.add_column("gmail_radar_items", sa.Column(
        "reason_code", sa.String(48), nullable=False, server_default="legacy"))
    op.add_column("gmail_radar_items", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("gmail_radar_items", sa.Column("due_text", sa.String(32), nullable=True))
    op.add_column("gmail_radar_scan_states", sa.Column("seven_day_count", sa.Integer(), nullable=True))
    op.add_column("gmail_radar_scan_states", sa.Column("seven_day_remaining", sa.Integer(), nullable=True))
    op.add_column("gmail_radar_scan_states", sa.Column(
        "seven_day_complete", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    raise RuntimeError("Gmail user evidence cannot be destructively downgraded without approval")
