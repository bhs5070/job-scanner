"""OpenAI embedding wrapper with batching support."""

import logging

from openai import OpenAI

from src.common.config import get_settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # OpenAI recommends batching for efficiency


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using OpenAI API.

    Processes in batches of BATCH_SIZE to respect API limits.
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]

        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=batch,
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

        logger.info(
            f"Embedded batch {i // BATCH_SIZE + 1}, "
            f"size={len(batch)}, total={len(all_embeddings)}"
        )

    return all_embeddings
