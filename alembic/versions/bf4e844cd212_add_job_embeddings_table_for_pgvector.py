"""add job_embeddings table for pgvector

Revision ID: bf4e844cd212
Revises: d2eea1c6eaf1
Create Date: 2026-04-09 16:13:24.042509
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'bf4e844cd212'
down_revision: Union[str, Sequence[str], None] = 'd2eea1c6eaf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Use 1536 dimensions (OpenAI supports dimension reduction)
    # HNSW index max is 2000 dimensions
    op.execute("""
        CREATE TABLE job_embeddings (
            id UUID PRIMARY KEY,
            job_posting_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
            chunk_type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute(
        "CREATE INDEX ix_job_embeddings_vector ON job_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_job_embeddings_job ON job_embeddings (job_posting_id, chunk_type)"
    )


def downgrade() -> None:
    op.drop_table("job_embeddings")
