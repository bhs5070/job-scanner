"""add bookmarks match_history conversations

Revision ID: 149c58a183fd
Revises: 3954468c2d81
Create Date: 2026-04-08 12:44:32.318092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '149c58a183fd'
down_revision: Union[str, Sequence[str], None] = '3954468c2d81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(200), nullable=False),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="interested"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bookmarks_user", "bookmarks", ["user_email", "created_at"])

    op.create_table(
        "match_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(200), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("intent", sa.String(50), nullable=False),
        sa.Column("results", postgresql.JSONB, nullable=True),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_match_history_user", "match_history", ["user_email", "created_at"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(200), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), server_default="새 대화"),
        sa.Column("messages", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user", "conversations", ["user_email", "updated_at"])


def downgrade() -> None:
    op.drop_table("conversations")
    op.drop_table("match_history")
    op.drop_table("bookmarks")
