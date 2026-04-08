"""add eval metrics columns

Revision ID: d2eea1c6eaf1
Revises: 3fb118fe4c0c
Create Date: 2026-04-08 16:22:06.215136
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2eea1c6eaf1'
down_revision: Union[str, Sequence[str], None] = '3fb118fe4c0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("eval_results", sa.Column("faithfulness", sa.Float, nullable=True))
    op.add_column("eval_results", sa.Column("answer_completeness", sa.Float, nullable=True))
    op.add_column("eval_results", sa.Column("retrieval_precision", sa.Float, nullable=True))
    op.add_column("eval_results", sa.Column("retrieval_mrr", sa.Float, nullable=True))
    op.add_column("eval_results", sa.Column("context_relevance", sa.Float, nullable=True))
    op.add_column("eval_results", sa.Column("routing_accuracy", sa.Float, nullable=True))
    op.add_column("eval_results", sa.Column("latency_ms", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("eval_results", "latency_ms")
    op.drop_column("eval_results", "routing_accuracy")
    op.drop_column("eval_results", "context_relevance")
    op.drop_column("eval_results", "retrieval_mrr")
    op.drop_column("eval_results", "retrieval_precision")
    op.drop_column("eval_results", "answer_completeness")
    op.drop_column("eval_results", "faithfulness")
