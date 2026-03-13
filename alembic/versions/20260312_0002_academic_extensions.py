"""academic domain extensions and attempt analytics

Revision ID: 20260312_0002
Revises: 20260309_0001
Create Date: 2026-03-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260312_0002"
down_revision = "20260309_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "academic_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_academic_sessions_slug", "academic_sessions", ["slug"], unique=True)

    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_semesters_slug", "semesters", ["slug"], unique=True)

    op.create_table(
        "programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_programs_slug", "programs", ["slug"], unique=True)
    op.create_index("ix_programs_code", "programs", ["code"], unique=True)

    op.create_table(
        "academic_calendar_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_session_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("semester_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "program_course_offerings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("academic_session_id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "program_id",
            "course_id",
            "level",
            "academic_session_id",
            "semester_id",
            name="uq_program_course_offering",
        ),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("academic_session_id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=True),
        sa.Column("assessment_type", sa.String(length=40), nullable=False),
        sa.Column("question_format", sa.String(length=40), nullable=False),
        sa.Column("year_label", sa.String(length=30), nullable=True),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_assessments_slug", "assessments", ["slug"], unique=True)

    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=False, server_default="student"))
    op.add_column("users", sa.Column("program_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("current_level", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("profile_update_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_foreign_key("fk_users_program_id", "users", "programs", ["program_id"], ["id"], ondelete="SET NULL")

    op.add_column("questions", sa.Column("assessment_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_questions_assessment", "questions", "assessments", ["assessment_id"], ["id"], ondelete="SET NULL")

    op.add_column("ai_question_generation_requests", sa.Column("assessment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ai_generation_assessment",
        "ai_question_generation_requests",
        "assessments",
        ["assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("quizzes", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("quizzes", sa.Column("reveal_answers_post_submit", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("quizzes", sa.Column("academic_session_id", sa.Integer(), nullable=True))
    op.add_column("quizzes", sa.Column("semester_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_quizzes_session", "quizzes", "academic_sessions", ["academic_session_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_quizzes_semester", "quizzes", "semesters", ["semester_id"], ["id"], ondelete="SET NULL")

    op.add_column("topic_performance", sa.Column("academic_session_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_topic_performance_session",
        "topic_performance",
        "academic_sessions",
        ["academic_session_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("quiz_id", "attempt_number", name="uq_quiz_attempt_number"),
    )

    op.add_column("quiz_responses", sa.Column("attempt_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_quiz_responses_attempt",
        "quiz_responses",
        "quiz_attempts",
        ["attempt_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column("quiz_results", sa.Column("attempt_id", sa.Integer(), nullable=True))
    op.execute("ALTER TABLE quiz_results DROP CONSTRAINT IF EXISTS quiz_results_quiz_id_key")
    op.create_foreign_key(
        "fk_quiz_results_attempt",
        "quiz_results",
        "quiz_attempts",
        ["attempt_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_quiz_results_attempt_id", "quiz_results", ["attempt_id"])

    op.create_table(
        "attempt_topic_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("academic_session_id", sa.Integer(), nullable=True),
        sa.Column("attempted_count", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("attempt_topic_metrics")
    op.drop_constraint("uq_quiz_results_attempt_id", "quiz_results", type_="unique")
    op.drop_constraint("fk_quiz_results_attempt", "quiz_results", type_="foreignkey")
    op.drop_column("quiz_results", "attempt_id")
    op.execute("ALTER TABLE quiz_results ADD CONSTRAINT quiz_results_quiz_id_key UNIQUE (quiz_id)")
    op.drop_constraint("fk_quiz_responses_attempt", "quiz_responses", type_="foreignkey")
    op.drop_column("quiz_responses", "attempt_id")
    op.drop_table("quiz_attempts")
    op.drop_constraint("fk_topic_performance_session", "topic_performance", type_="foreignkey")
    op.drop_column("topic_performance", "academic_session_id")
    op.drop_constraint("fk_quizzes_semester", "quizzes", type_="foreignkey")
    op.drop_constraint("fk_quizzes_session", "quizzes", type_="foreignkey")
    op.drop_column("quizzes", "semester_id")
    op.drop_column("quizzes", "academic_session_id")
    op.drop_column("quizzes", "reveal_answers_post_submit")
    op.drop_column("quizzes", "max_attempts")

    op.drop_constraint("fk_ai_generation_assessment", "ai_question_generation_requests", type_="foreignkey")
    op.drop_column("ai_question_generation_requests", "assessment_id")

    op.drop_constraint("fk_questions_assessment", "questions", type_="foreignkey")
    op.drop_column("questions", "assessment_id")

    op.drop_constraint("fk_users_program_id", "users", type_="foreignkey")
    op.drop_column("users", "profile_update_required")
    op.drop_column("users", "current_level")
    op.drop_column("users", "program_id")
    op.drop_column("users", "role")

    op.drop_index("ix_assessments_slug", table_name="assessments")
    op.drop_table("assessments")
    op.drop_table("program_course_offerings")
    op.drop_table("academic_calendar_state")
    op.drop_index("ix_programs_code", table_name="programs")
    op.drop_index("ix_programs_slug", table_name="programs")
    op.drop_table("programs")
    op.drop_index("ix_semesters_slug", table_name="semesters")
    op.drop_table("semesters")
    op.drop_index("ix_academic_sessions_slug", table_name="academic_sessions")
    op.drop_table("academic_sessions")
