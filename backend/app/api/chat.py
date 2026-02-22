import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.pipeline.retriever import hybrid_search
from app.prompts.rag_answer import build_rag_prompt
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.config import settings
from app.services.openai_client import get_openai, with_backoff

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.post("")
async def chat(
    req: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Hybrid search for relevant chunks
    chunks = await hybrid_search(
        db=db,
        user_id=user.id,
        query=req.query,
        filters=req.filters,
        top_k=6,
    )

    if not chunks:
        async def empty_stream():
            data = ChatResponse(
                answer="I couldn't find any relevant information in your connected tools. Try connecting more data sources or rephrasing your question.",
                citations=[],
                confidence=0.0,
            ).model_dump_json()
            yield {"event": "result", "data": data}

        return EventSourceResponse(empty_stream())

    # 2. Build RAG prompt with retrieved chunks
    messages = build_rag_prompt(query=req.query, chunks=chunks)

    # 3. Stream the response via SSE
    async def generate():
        client = get_openai()
        full_answer = ""

        stream = await with_backoff(
            client.chat.completions.create,
            model=settings.llm_model,
            messages=messages,
            stream=True,
            temperature=0.1,
        )

        async for event in stream:
            delta = event.choices[0].delta
            if delta.content:
                full_answer += delta.content
                yield {"event": "token", "data": delta.content}

        # Build citations from the retrieved chunks
        citations = []
        for i, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            citations.append(Citation(
                index=i + 1,
                title=meta.get("title"),
                url=meta.get("url"),
                snippet=chunk["content"][:200],
                author_name=meta.get("author_name"),
                provider=meta.get("provider", "unknown"),
                source_created_at=meta.get("source_created_at"),
                metadata=meta,
            ))

        result = ChatResponse(
            answer=full_answer,
            citations=citations,
            confidence=0.8 if chunks else 0.0,
        )
        yield {"event": "result", "data": result.model_dump_json()}

    return EventSourceResponse(generate())
