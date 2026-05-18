"""question import job tracking

Revision ID: 20260518_0006
Revises: 20260508_0005
Create Date: 2026-05-18 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260518_0006"
down_revision = "20260508_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="json"),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("import_mode", sa.String(length=30), nullable=False, server_default="mixed"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("row_errors", sa.JSON(), nullable=True),
        sa.Column("created_question_ids", sa.JSON(), nullable=True),
        sa.Column("created_topic_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_question_import_jobs_created_by_user_id", "question_import_jobs", ["created_by_user_id"])
    op.create_index("ix_question_import_jobs_created_at", "question_import_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_question_import_jobs_created_at", table_name="question_import_jobs")
    op.drop_index("ix_question_import_jobs_created_by_user_id", table_name="question_import_jobs")
    op.drop_table("question_import_jobs")
