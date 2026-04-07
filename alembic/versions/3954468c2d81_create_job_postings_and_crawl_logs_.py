"""create job_postings and crawl_logs tables

Revision ID: 3954468c2d81
Revises:
Create Date: 2026-04-08 00:12:17.204223

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3954468c2d81'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requirements", sa.Text, nullable=True),
        sa.Column("tech_stack", postgresql.JSONB, nullable=True),
        sa.Column("source_url", sa.Text, nullable=False, unique=True),
        sa.Column("source_site", sa.String(50), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_job_postings_site_collected",
        "job_postings",
        ["source_site", sa.text("collected_at DESC")],
    )
    op.create_index(
        "ix_job_postings_unindexed",
        "job_postings",
        ["is_active", "indexed_at"],
        postgresql_where=sa.text("indexed_at IS NULL"),
    )
    op.create_index(
        "ix_job_postings_tech_stack",
        "job_postings",
        ["tech_stack"],
        postgresql_using="gin",
    )

    op.create_table(
        "crawl_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_site", sa.String(50), nullable=False),
        sa.Column("dag_run_id", sa.String(200), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("total_fetched", sa.Integer, server_default="0"),
        sa.Column("total_saved", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("crawl_logs")
    op.drop_index("ix_job_postings_tech_stack", table_name="job_postings")
    op.drop_index("ix_job_postings_unindexed", table_name="job_postings")
    op.drop_index("ix_job_postings_site_collected", table_name="job_postings")
    op.drop_table("job_postings")
