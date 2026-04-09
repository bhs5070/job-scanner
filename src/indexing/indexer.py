"""pgvector indexer for job posting embeddings."""

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.indexing.chunker import JDChunk

logger = logging.getLogger(__name__)


def upsert_chunks(
    db: Session,
    chunks: list[JDChunk],
    embeddings: list[list[float]],
) -> int:
    """Upsert chunks with embeddings into job_embeddings table."""
    if not chunks:
        return 0

    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        doc_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{chunk.job_id}_{chunk.chunk_type}")
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        db.execute(text("""
            INSERT INTO job_embeddings (id, job_posting_id, chunk_type, content, embedding)
            VALUES (:id, :job_id, :chunk_type, :content, :embedding)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding
        """), {
            "id": str(doc_id),
            "job_id": chunk.job_id,
            "chunk_type": chunk.chunk_type,
            "content": chunk.text,
            "embedding": embedding_str,
        })
        count += 1

    db.commit()
    logger.info(f"Upserted {count} chunks to pgvector")
    return count
