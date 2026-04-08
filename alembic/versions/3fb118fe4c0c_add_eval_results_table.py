"""add eval_results table

Revision ID: 3fb118fe4c0c
Revises: 2c16b3f473d7
Create Date: 2026-04-08 15:53:09.270586
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3fb118fe4c0c'
down_revision: Union[str, Sequence[str], None] = '2c16b3f473d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_history_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("match_history.id"), nullable=True),
        sa.Column("intent", sa.String(50), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("relevance", sa.Float, nullable=True),
        sa.Column("groundedness", sa.Float, nullable=True),
        sa.Column("helpfulness", sa.Float, nullable=True),
        sa.Column("avg_score", sa.Float, nullable=True),
        sa.Column("judge_reasoning", sa.Text, nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_eval_results_evaluated", "eval_results", ["evaluated_at"])


def downgrade() -> None:
    op.drop_table("eval_results")
