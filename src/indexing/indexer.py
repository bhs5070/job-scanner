"""ChromaDB indexer for job posting vectors."""

import logging

import chromadb

from src.common.config import get_settings
from src.indexing.chunker import JDChunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "job_scanner_jds"


def get_chroma_client() -> chromadb.ClientAPI:
    """Create a persistent ChromaDB client."""
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.CHROMADB_PATH)


def get_or_create_collection(
    client: chromadb.ClientAPI,
) -> chromadb.Collection:
    """Get or create the JD collection."""
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Job posting vectors for RAG search"},
    )


def upsert_chunks(
    collection: chromadb.Collection,
    chunks: list[JDChunk],
    embeddings: list[list[float]],
) -> int:
    """Upsert chunks with their embeddings into ChromaDB.

    Returns the number of upserted documents.
    """
    if not chunks:
        return 0

    ids = [f"{chunk.job_id}_{chunk.chunk_type}" for chunk in chunks]
    documents = [chunk.text for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info(f"Upserted {len(ids)} chunks to ChromaDB")
    return len(ids)


def deactivate_jobs(
    collection: chromadb.Collection, job_ids: list[str]
) -> None:
    """Mark job postings as inactive in ChromaDB metadata."""
    for job_id in job_ids:
        # Update both chunk types
        for chunk_type in ["full", "requirements"]:
            doc_id = f"{job_id}_{chunk_type}"
            try:
                collection.update(
                    ids=[doc_id],
                    metadatas=[{"is_active": False}],
                )
            except Exception as e:
                logger.debug(f"Chunk {doc_id} not found, skipping: {e}")
