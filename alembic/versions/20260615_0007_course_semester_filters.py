"""add semester foreign key to courses

Revision ID: 20260615_0007
Revises: 20260518_0006
Create Date: 2026-06-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260615_0007"
down_revision = "20260518_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("semester_id", sa.Integer(), nullable=True))
    op.create_index("ix_courses_semester_id", "courses", ["semester_id"], unique=False)
    op.create_foreign_key(
        "fk_courses_semester_id_semesters",
        "courses",
        "semesters",
        ["semester_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE courses AS c
        SET semester_id = s.id
        FROM semesters AS s
        WHERE c.semester_id IS NULL
          AND c.semester IS NOT NULL
          AND (
            lower(trim(c.semester)) = lower(trim(s.name))
            OR lower(trim(c.semester)) = lower(trim(s.slug))
          )
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_courses_semester_id_semesters", "courses", type_="foreignkey")
    op.drop_index("ix_courses_semester_id", table_name="courses")
    op.drop_column("courses", "semester_id")
