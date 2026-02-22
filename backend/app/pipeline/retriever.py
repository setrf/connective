import json
import logging
import uuid

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import Float, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import cast, select, text

from app.config import settings
from app.models.chunk import Chunk
from app.models.document_access import DocumentAccess
from app.pipeline.embedder import embed_query
from app.services.openai_client import get_openai, with_backoff

logger = logging.getLogger("uvicorn.error")


def _accessible_doc_ids(user_id: uuid.UUID):
    """Subquery returning document IDs the user has access to."""
    return (
        select(DocumentAccess.document_id)
        .where(DocumentAccess.user_id == user_id)
        .scalar_subquery()
    )


async def _llm_rerank(
    query: str, candidates: list[dict], top_k: int = 6
) -> list[dict]:
    """Rerank candidates using LLM scoring. Takes top 10, returns top_k."""
    if len(candidates) <= top_k:
        return candidates

    # Take top 10 for reranking
    to_rerank = candidates[:10]

    numbered = "\n".join(
        f"[{i}] {c['content'][:300]}" for i, c in enumerate(to_rerank)
    )

    client = get_openai()
    response = await with_backoff(
        client.chat.completions.create,
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a relevance scorer. Given a query and numbered passages, "
                    "return a JSON array of the passage indices sorted by relevance "
                    "(most relevant first). Only return the JSON array, nothing else. "
                    "Example: [3, 0, 7, 1, 5, 2]"
                ),
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nPassages:\n{numbered}",
            },
        ],
        temperature=0.0,
    )

    try:
        content = response.choices[0].message.content or "[]"
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        ranking = json.loads(content)
        reranked = []
        for idx in ranking:
            if isinstance(idx, int) and 0 <= idx < len(to_rerank):
                reranked.append(to_rerank[idx])
        # Add any candidates missed by LLM
        seen = set(ranking)
        for i, c in enumerate(to_rerank):
            if i not in seen:
                reranked.append(c)
        return reranked[:top_k]
    except (json.JSONDecodeError, TypeError, KeyError):
        logger.warning("LLM reranking failed, falling back to RRF order")
        return candidates[:top_k]


async def hybrid_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    filters: dict | None = None,
    top_k: int = 6,
    vector_top: int = 40,
    fts_top: int = 40,
    rrf_k: int = 60,
    rerank: bool = True,
) -> list[dict]:
    """Hybrid search: vector + full-text search with Reciprocal Rank Fusion + LLM reranking.

    Uses document_access to filter chunks the user can see, enabling
    cross-user deduplication.
    """

    # Subquery: document IDs this user can access
    accessible_docs = _accessible_doc_ids(user_id)

    # 1. Embed the query
    query_embedding = await embed_query(query)

    # 2. Vector search — cosine distance via halfvec cast (ethelflow pattern)
    distance = (
        cast(Chunk.embedding, HALFVEC(1536))
        .op("<=>")(cast(query_embedding, HALFVEC(1536)))
        .cast(Float)
        .label("distance")
    )

    vector_stmt = (
        select(Chunk.id, Chunk.content, Chunk.metadata_, distance)
        .where(Chunk.document_id.in_(accessible_docs))
        .order_by(distance)
        .limit(vector_top)
    )

    # Apply filters
    if filters:
        if filters.get("providers"):
            vector_stmt = vector_stmt.where(
                Chunk.metadata_["provider"].astext.in_(filters["providers"])
            )

    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    vector_results = (await db.execute(vector_stmt)).all()

    # 3. Full-text search
    ts_query = func.plainto_tsquery("english", query)
    fts_rank = func.ts_rank(Chunk.fts, ts_query).cast(Float).label("rank")

    fts_stmt = (
        select(Chunk.id, Chunk.content, Chunk.metadata_, fts_rank)
        .where(Chunk.document_id.in_(accessible_docs))
        .where(Chunk.fts.op("@@")(ts_query))
        .order_by(fts_rank.desc())
        .limit(fts_top)
    )

    if filters:
        if filters.get("providers"):
            fts_stmt = fts_stmt.where(
                Chunk.metadata_["provider"].astext.in_(filters["providers"])
            )

    fts_results = (await db.execute(fts_stmt)).all()

    # 4. Reciprocal Rank Fusion
    scores: dict[uuid.UUID, dict] = {}

    for rank, row in enumerate(vector_results):
        chunk_id = row.id
        rrf_score = 1.0 / (rrf_k + rank + 1)
        scores[chunk_id] = {
            "content": row.content,
            "metadata": row.metadata_,
            "score": rrf_score,
        }

    for rank, row in enumerate(fts_results):
        chunk_id = row.id
        rrf_score = 1.0 / (rrf_k + rank + 1)
        if chunk_id in scores:
            scores[chunk_id]["score"] += rrf_score
        else:
            scores[chunk_id] = {
                "content": row.content,
                "metadata": row.metadata_,
                "score": rrf_score,
            }

    # 5. Sort by RRF score
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

    logger.info(
        f"Hybrid search: {len(vector_results)} vector + {len(fts_results)} FTS "
        f"→ {len(scores)} unique"
    )

    # 6. LLM reranking (top 10 → top_k)
    if rerank and len(ranked) > top_k:
        ranked = await _llm_rerank(query, ranked, top_k=top_k)
        logger.info(f"After LLM reranking: {len(ranked)} results")
    else:
        ranked = ranked[:top_k]

    return ranked
