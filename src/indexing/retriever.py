"""pgvector-based retriever for job posting search."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.common.config import get_settings
from src.indexing.embedder import get_embeddings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 1536  # Reduced from 3072 for HNSW index compatibility


@dataclass
class SearchResult:
    """A single search result."""

    job_id: str
    chunk_type: str
    document: str
    metadata: dict
    distance: float


def get_embeddings_reduced(texts: list[str]) -> list[list[float]]:
    """Generate embeddings with reduced dimensions for pgvector."""
    settings = get_settings()
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=batch,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def search_jobs(
    query: str,
    n_results: int = 10,
    where: dict | None = None,
    db: Session | None = None,
) -> list[SearchResult]:
    """Search for job postings using pgvector similarity.

    Args:
        query: Search query text.
        n_results: Number of results to return.
        where: Metadata filters (is_active, chunk_type).
        db: SQLAlchemy session. If None, creates one.
    """
    from src.db.session import SessionLocal

    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        # Embed the query
        query_embedding = get_embeddings_reduced([query])[0]
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Build SQL query with filters
        conditions = []
        if where:
            if where.get("is_active") is True:
                conditions.append("jp.is_active = true")
            if where.get("chunk_type"):
                conditions.append(f"je.chunk_type = '{where['chunk_type']}'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = text(f"""
            SELECT
                je.job_posting_id::text,
                je.chunk_type,
                je.content,
                jp.title,
                jp.company,
                jp.source_site,
                jp.source_url,
                jp.is_active,
                je.embedding <=> :embedding AS distance
            FROM job_embeddings je
            JOIN job_postings jp ON je.job_posting_id = jp.id
            WHERE {where_clause}
            ORDER BY je.embedding <=> :embedding
            LIMIT :limit
        """)

        rows = db.execute(sql, {"embedding": embedding_str, "limit": n_results}).fetchall()

        results = []
        for row in rows:
            results.append(SearchResult(
                job_id=row[0],
                chunk_type=row[1],
                document=row[2],
                metadata={
                    "job_id": row[0],
                    "title": row[3],
                    "company": row[4],
                    "source_site": row[5],
                    "source_url": row[6],
                    "is_active": row[7],
                    "chunk_type": row[1],
                },
                distance=float(row[8]),
            ))

        return results

    finally:
        if own_session:
            db.close()
