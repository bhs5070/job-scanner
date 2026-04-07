"""Indexing pipeline: DB -> chunk -> embed -> ChromaDB.

This is the main entry point called by the Airflow DAG.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.db.crud.job_postings import get_unindexed_jobs, mark_as_indexed
from src.indexing.chunker import JDChunk, chunk_job_posting
from src.indexing.embedder import get_embeddings
from src.indexing.indexer import get_chroma_client, get_or_create_collection, upsert_chunks

logger = logging.getLogger(__name__)


def run_incremental_index(db: Session, batch_size: int = 100) -> dict:
    """Run incremental indexing for unindexed job postings.

    1. Query DB for jobs where indexed_at IS NULL
    2. Chunk each job into semantic sections
    3. Embed all chunks via OpenAI
    4. Upsert into ChromaDB
    5. Mark jobs as indexed in DB

    Returns a summary dict with counts.
    """
    jobs = get_unindexed_jobs(db, limit=batch_size)

    if not jobs:
        logger.info("No unindexed jobs found. Skipping.")
        return {"total_jobs": 0, "total_chunks": 0, "indexed": 0}

    logger.info(f"Found {len(jobs)} unindexed jobs to process")

    # Step 1: Chunk all jobs
    all_chunks: list[JDChunk] = []
    for job in jobs:
        chunks = chunk_job_posting(job)
        all_chunks.extend(chunks)

    logger.info(f"Generated {len(all_chunks)} chunks from {len(jobs)} jobs")

    if not all_chunks:
        return {"total_jobs": len(jobs), "total_chunks": 0, "indexed": 0}

    # Step 2: Embed all chunks
    texts = [chunk.text for chunk in all_chunks]
    embeddings = get_embeddings(texts)

    # Step 3: Upsert into ChromaDB
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    upserted = upsert_chunks(collection, all_chunks, embeddings)

    # Step 4: Mark as indexed in DB
    job_ids = [job.id for job in jobs]
    mark_as_indexed(db, job_ids)

    summary = {
        "total_jobs": len(jobs),
        "total_chunks": len(all_chunks),
        "indexed": upserted,
    }
    logger.info(f"Indexing complete: {summary}")
    return summary
