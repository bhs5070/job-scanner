"""add user_profiles table

Revision ID: 2c16b3f473d7
Revises: 149c58a183fd
Create Date: 2026-04-08 12:53:52.835392
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2c16b3f473d7'
down_revision: Union[str, Sequence[str], None] = '149c58a183fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(200), primary_key=True),  # email as PK
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("career_type", sa.String(50), nullable=True),
        sa.Column("job_category", sa.String(50), nullable=True),
        sa.Column("tech_stack", sa.Text, nullable=True),
        sa.Column("education", sa.String(50), nullable=True),
        sa.Column("major", sa.String(100), nullable=True),
        sa.Column("salary_range", sa.String(50), nullable=True),
        sa.Column("location_pref", sa.String(50), nullable=True),
        sa.Column("resume_text", sa.Text, nullable=True),
        sa.Column("portfolio_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
