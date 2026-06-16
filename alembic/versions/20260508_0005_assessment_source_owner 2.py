"""assessment source type and owner for user-generated AI sets

Revision ID: 20260508_0005
Revises: 20260505_0004
Create Date: 2026-05-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260508_0005"
down_revision = "20260505_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("source_type", sa.String(length=30), nullable=False, server_default="actual"))
    op.add_column("assessments", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_assessments_created_by_user",
        "assessments",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_assessments_created_by_user", "assessments", type_="foreignkey")
    op.drop_column("assessments", "created_by_user_id")
    op.drop_column("assessments", "source_type")
