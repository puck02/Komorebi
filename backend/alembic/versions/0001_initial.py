"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("style", sa.JSON(), nullable=False),
        sa.Column("colors", sa.JSON(), nullable=False),
        sa.Column("file", sa.String(length=512), nullable=False),
        sa.Column("license", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("quality_status", sa.String(length=40), nullable=False),
    )
    op.create_index("ix_assets_category", "assets", ["category"])
    op.create_index("ix_assets_quality_status", "assets", ["quality_status"])

    op.create_table(
        "images",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_path", sa.String(length=1024), nullable=False),
        sa.Column("thumbnail_path", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_images_user_id", "images", ["user_id"])

    op.create_table(
        "journals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("journal_date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("mood_tags", sa.JSON(), nullable=False),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_journals_user_id", "journals", ["user_id"])

    op.create_table(
        "journal_images",
        sa.Column("journal_id", sa.String(length=36), sa.ForeignKey("journals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image_id", sa.String(length=36), sa.ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("journal_images")
    op.drop_index("ix_journals_user_id", table_name="journals")
    op.drop_table("journals")
    op.drop_index("ix_images_user_id", table_name="images")
    op.drop_table("images")
    op.drop_index("ix_assets_quality_status", table_name="assets")
    op.drop_index("ix_assets_category", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
