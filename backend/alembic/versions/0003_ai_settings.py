"""Add administrator AI settings.

Revision ID: 0003_ai_settings
Revises: 0002_generation_jobs
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_ai_settings"
down_revision = "0002_generation_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("base_url", sa.String(length=1024), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("review_model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
