"""add user_feedback table

Revision ID: a4ac64232e2f
Revises: bf4e844cd212
Create Date: 2026-04-09 16:32:22.811623
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a4ac64232e2f'
down_revision: Union[str, Sequence[str], None] = 'bf4e844cd212'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(200), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("feedback", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_feedback_user", "user_feedback", ["user_email"])


def downgrade() -> None:
    op.drop_table("user_feedback")
