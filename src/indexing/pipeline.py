"""Indexing pipeline: DB -> chunk -> embed -> pgvector."""

import logging

from sqlalchemy.orm import Session

from src.db.crud.job_postings import get_unindexed_jobs, mark_as_indexed
from src.indexing.chunker import JDChunk, chunk_job_posting
from src.indexing.indexer import upsert_chunks
from src.indexing.retriever import get_embeddings_reduced

logger = logging.getLogger(__name__)


def run_incremental_index(db: Session, batch_size: int = 100) -> dict:
    """Run incremental indexing for unindexed job postings.

    Uses pgvector with 1536-dimension embeddings.
    """
    jobs = get_unindexed_jobs(db, limit=batch_size)

    if not jobs:
        logger.info("No unindexed jobs found.")
        return {"total_jobs": 0, "total_chunks": 0, "indexed": 0}

    logger.info(f"Found {len(jobs)} unindexed jobs")

    # Chunk
    all_chunks: list[JDChunk] = []
    for job in jobs:
        chunks = chunk_job_posting(job)
        all_chunks.extend(chunks)

    if not all_chunks:
        return {"total_jobs": len(jobs), "total_chunks": 0, "indexed": 0}

    # Embed (1536 dimensions for pgvector HNSW)
    texts = [chunk.text for chunk in all_chunks]
    embeddings = get_embeddings_reduced(texts)

    # Upsert to pgvector
    upserted = upsert_chunks(db, all_chunks, embeddings)

    # Mark as indexed
    job_ids = [job.id for job in jobs]
    mark_as_indexed(db, job_ids)

    summary = {"total_jobs": len(jobs), "total_chunks": len(all_chunks), "indexed": upserted}
    logger.info(f"Indexing complete: {summary}")
    return summary
