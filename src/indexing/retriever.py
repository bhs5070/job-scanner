"""ChromaDB retriever for job posting search."""

import logging
from dataclasses import dataclass

import chromadb

from src.indexing.embedder import get_embeddings
from src.indexing.indexer import COLLECTION_NAME, get_chroma_client, get_or_create_collection

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from ChromaDB."""

    job_id: str
    chunk_type: str
    document: str
    metadata: dict
    distance: float


def search_jobs(
    query: str,
    n_results: int = 10,
    where: dict | None = None,
) -> list[SearchResult]:
    """Search for job postings similar to the query.

    Args:
        query: Search query text.
        n_results: Number of results to return.
        where: Optional metadata filter (e.g., {"is_active": True}).
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # Embed the query
    query_embedding = get_embeddings([query])[0]

    # Default filter: only active jobs
    if where is None:
        where = {"is_active": True}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    search_results: list[SearchResult] = []
    if not results["ids"] or not results["ids"][0]:
        return search_results

    for i, doc_id in enumerate(results["ids"][0]):
        parts = doc_id.rsplit("_", 1)
        job_id = parts[0] if len(parts) == 2 else doc_id
        chunk_type = parts[1] if len(parts) == 2 else "full"

        search_results.append(SearchResult(
            job_id=job_id,
            chunk_type=chunk_type,
            document=results["documents"][0][i],
            metadata=results["metadatas"][0][i],
            distance=results["distances"][0][i],
        ))

    return search_results
