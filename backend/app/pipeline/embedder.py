import logging

from app.config import settings
from app.services.openai_client import get_openai, with_backoff

logger = logging.getLogger("uvicorn.error")

BATCH_SIZE = 100


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using OpenAI, batching at 100 per request."""
    client = get_openai()
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info(f"Embedding batch {i // BATCH_SIZE + 1} ({len(batch)} texts)")

        response = await with_backoff(
            client.embeddings.create,
            input=batch,
            model=settings.embedding_model,
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    client = get_openai()
    response = await with_backoff(
        client.embeddings.create,
        input=[query],
        model=settings.embedding_model,
    )
    return response.data[0].embedding
