import datetime
import json
import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user, get_db
from app.database import get_session_ctx
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.pipeline.retriever import hybrid_search
from app.prompts.rag_answer import build_rag_prompt
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    Citation,
)
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
    # Persist user message
    user_msg = ChatMessage(
        user_id=user.id,
        role="user",
        content=req.query,
    )
    db.add(user_msg)
    await db.flush()
    user_msg_id = str(user_msg.id)

    # 1. Hybrid search for relevant chunks
    chunks = await hybrid_search(
        db=db,
        user_id=user.id,
        query=req.query,
        filters=req.filters,
        top_k=6,
    )

    if not chunks:
        empty_answer = "I couldn't find any relevant information in your connected tools. Try connecting more data sources or rephrasing your question."

        # Persist empty assistant message
        asst_msg = ChatMessage(
            user_id=user.id,
            role="assistant",
            content=empty_answer,
            confidence=0.0,
        )
        db.add(asst_msg)
        await db.commit()

        async def empty_stream():
            data = ChatResponse(
                answer=empty_answer,
                citations=[],
                confidence=0.0,
                user_message_id=user_msg_id,
                assistant_message_id=str(asst_msg.id),
            ).model_dump_json()
            yield {"event": "result", "data": data}

        return EventSourceResponse(empty_stream())

    # 2. Build RAG prompt with retrieved chunks
    messages = build_rag_prompt(query=req.query, chunks=chunks)

    # Commit the user message before streaming (so it's visible in history)
    await db.commit()

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

        # Persist assistant message
        async with get_session_ctx() as persist_db:
            asst_msg = ChatMessage(
                user_id=user.id,
                role="assistant",
                content=full_answer,
                citations=[c.model_dump(mode="json") for c in citations],
                confidence=0.8 if chunks else 0.0,
            )
            persist_db.add(asst_msg)
            await persist_db.commit()

            result = ChatResponse(
                answer=full_answer,
                citations=citations,
                confidence=0.8 if chunks else 0.0,
                user_message_id=user_msg_id,
                assistant_message_id=str(asst_msg.id),
            )
            yield {"event": "result", "data": result.model_dump_json()}

    return EventSourceResponse(generate())


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(
    before: datetime.datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cursor-paginated chat history, newest first, reversed to chronological."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
    )

    if before:
        stmt = stmt.where(ChatMessage.created_at < before)

    stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    # Reverse to chronological order
    rows.reverse()

    messages = [
        ChatMessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            citations=msg.citations,
            confidence=msg.confidence,
            metadata=msg.metadata_,
            created_at=msg.created_at,
        )
        for msg in rows
    ]

    return ChatHistoryResponse(messages=messages, has_more=has_more)
