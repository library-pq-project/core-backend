"""assessment duration, attempt timing, question content format, lecture storage metadata

Revision ID: 20260313_0003
Revises: 20260312_0002
Create Date: 2026-03-13 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0003"
down_revision = "20260312_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("default_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
    )

    op.add_column("questions", sa.Column("source_text", sa.Text(), nullable=True))
    op.add_column(
        "questions",
        sa.Column("content_format", sa.String(length=30), nullable=False, server_default="plain_text"),
    )
    op.execute("UPDATE questions SET source_text = question_text WHERE source_text IS NULL")

    op.add_column("quizzes", sa.Column("assessment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_quizzes_assessment",
        "quizzes",
        "assessments",
        ["assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("quiz_attempts", sa.Column("expected_end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quiz_attempts", sa.Column("duration_used_seconds", sa.Integer(), nullable=True))
    op.add_column(
        "quiz_attempts",
        sa.Column("selected_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
    )

    op.add_column(
        "lecture_notes",
        sa.Column("storage_provider", sa.String(length=30), nullable=False, server_default="local"),
    )
    op.add_column("lecture_notes", sa.Column("storage_bucket", sa.String(length=120), nullable=True))
    op.add_column("lecture_notes", sa.Column("storage_key", sa.String(length=255), nullable=True))
    op.execute("UPDATE lecture_notes SET storage_key = stored_file_name WHERE storage_key IS NULL")


def downgrade() -> None:
    op.drop_column("lecture_notes", "storage_key")
    op.drop_column("lecture_notes", "storage_bucket")
    op.drop_column("lecture_notes", "storage_provider")

    op.drop_column("quiz_attempts", "selected_duration_minutes")
    op.drop_column("quiz_attempts", "duration_used_seconds")
    op.drop_column("quiz_attempts", "expected_end_at")

    op.drop_constraint("fk_quizzes_assessment", "quizzes", type_="foreignkey")
    op.drop_column("quizzes", "assessment_id")

    op.drop_column("questions", "content_format")
    op.drop_column("questions", "source_text")

    op.drop_column("assessments", "default_duration_minutes")
