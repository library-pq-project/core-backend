"""course compacts, ai request enrichment, theory upload/grading fields

Revision ID: 20260505_0004
Revises: 20260313_0003
Create Date: 2026-05-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260505_0004"
down_revision = "20260313_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course_compacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_provider", sa.String(length=30), nullable=False, server_default="local"),
        sa.Column("storage_bucket", sa.String(length=120), nullable=True),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("compact_summary", sa.Text(), nullable=True),
        sa.Column("taxonomy_text", sa.Text(), nullable=True),
        sa.Column("key_terms_text", sa.Text(), nullable=True),
        sa.Column("pitfalls_text", sa.Text(), nullable=True),
        sa.Column("text_extraction_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint("course_id", "version", name="uq_course_compact_version"),
    )
    op.create_index("ix_course_compacts_slug", "course_compacts", ["slug"], unique=True)

    op.add_column("lecture_notes", sa.Column("relevance_score", sa.Numeric(5, 4), nullable=True))
    op.add_column("lecture_notes", sa.Column("relevance_status", sa.String(length=30), nullable=False, server_default="pending"))
    op.add_column("lecture_notes", sa.Column("relevance_reason", sa.Text(), nullable=True))

    op.add_column("questions", sa.Column("marking_scheme", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("ai_topic_confidence", sa.Numeric(5, 4), nullable=True))
    op.add_column("questions", sa.Column("ai_topic_trace", sa.JSON(), nullable=True))

    op.add_column("ai_question_generation_requests", sa.Column("quiz_title", sa.String(length=255), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("user_prompt", sa.String(length=2000), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("exam_type", sa.String(length=30), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("difficulty_level", sa.String(length=30), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("model_name", sa.String(length=120), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("estimated_input_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("estimated_output_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_question_generation_requests", sa.Column("failure_reason", sa.String(length=500), nullable=True))

    op.execute("UPDATE ai_question_generation_requests SET quiz_title = 'AI Practice' WHERE quiz_title IS NULL")
    op.execute("UPDATE ai_question_generation_requests SET user_prompt = 'Generate questions' WHERE user_prompt IS NULL")
    op.execute("UPDATE ai_question_generation_requests SET exam_type = 'objective' WHERE exam_type IS NULL")
    op.execute("UPDATE ai_question_generation_requests SET difficulty_level = 'mixed' WHERE difficulty_level IS NULL")
    op.alter_column("ai_question_generation_requests", "quiz_title", nullable=False)
    op.alter_column("ai_question_generation_requests", "user_prompt", nullable=False)
    op.alter_column("ai_question_generation_requests", "exam_type", nullable=False)
    op.alter_column("ai_question_generation_requests", "difficulty_level", nullable=False)

    op.add_column("quiz_responses", sa.Column("answer_input_mode", sa.String(length=20), nullable=False, server_default="typed"))
    op.add_column("quiz_responses", sa.Column("answer_file_provider", sa.String(length=30), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_file_bucket", sa.String(length=120), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_file_key", sa.String(length=255), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_file_path", sa.String(length=500), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_file_type", sa.String(length=20), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_file_size", sa.Integer(), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_extracted_text", sa.Text(), nullable=True))
    op.add_column("quiz_responses", sa.Column("answer_extraction_status", sa.String(length=30), nullable=False, server_default="pending"))
    op.add_column("quiz_responses", sa.Column("grading_strengths", sa.Text(), nullable=True))
    op.add_column("quiz_responses", sa.Column("grading_missing_points", sa.Text(), nullable=True))
    op.add_column("quiz_responses", sa.Column("grading_confidence", sa.Numeric(5, 4), nullable=True))
    op.add_column("quiz_responses", sa.Column("grading_explanation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("quiz_responses", "grading_explanation")
    op.drop_column("quiz_responses", "grading_confidence")
    op.drop_column("quiz_responses", "grading_missing_points")
    op.drop_column("quiz_responses", "grading_strengths")
    op.drop_column("quiz_responses", "answer_extraction_status")
    op.drop_column("quiz_responses", "answer_extracted_text")
    op.drop_column("quiz_responses", "answer_file_size")
    op.drop_column("quiz_responses", "answer_file_type")
    op.drop_column("quiz_responses", "answer_file_path")
    op.drop_column("quiz_responses", "answer_file_key")
    op.drop_column("quiz_responses", "answer_file_bucket")
    op.drop_column("quiz_responses", "answer_file_provider")
    op.drop_column("quiz_responses", "answer_input_mode")

    op.drop_column("ai_question_generation_requests", "failure_reason")
    op.drop_column("ai_question_generation_requests", "estimated_output_tokens")
    op.drop_column("ai_question_generation_requests", "estimated_input_tokens")
    op.drop_column("ai_question_generation_requests", "model_name")
    op.drop_column("ai_question_generation_requests", "difficulty_level")
    op.drop_column("ai_question_generation_requests", "exam_type")
    op.drop_column("ai_question_generation_requests", "user_prompt")
    op.drop_column("ai_question_generation_requests", "quiz_title")

    op.drop_column("questions", "ai_topic_trace")
    op.drop_column("questions", "ai_topic_confidence")
    op.drop_column("questions", "marking_scheme")

    op.drop_column("lecture_notes", "relevance_reason")
    op.drop_column("lecture_notes", "relevance_status")
    op.drop_column("lecture_notes", "relevance_score")

    op.drop_index("ix_course_compacts_slug", table_name="course_compacts")
    op.drop_table("course_compacts")
