"""Add generation jobs.

Revision ID: 0002_generation_jobs
Revises: 0001_initial
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_generation_jobs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("revision_round", sa.Integer(), nullable=False),
        sa.Column("max_revision_rounds", sa.Integer(), nullable=False),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column("journal_id", sa.String(length=36), sa.ForeignKey("journals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_generation_jobs_user_id", "generation_jobs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_user_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
