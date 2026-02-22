import logging
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.pipeline.retriever import hybrid_search
from app.prompts.scan_overlap import build_scan_prompt
from app.schemas.scan import (
    OverlapItem,
    PersonOverlap,
    ScanRequest,
    ScanResponse,
)
from app.config import settings
from app.services.openai_client import get_openai, with_backoff

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.post("", response_model=ScanResponse)
async def scan(
    req: ScanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Use the content as the query for hybrid search
    query = req.content[:1000]  # Truncate for embedding

    chunks = await hybrid_search(
        db=db,
        user_id=user.id,
        query=query,
        top_k=10,
    )

    # Build overlaps
    overlaps = []
    people: dict[str, dict] = {}

    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        overlaps.append(OverlapItem(
            title=meta.get("title"),
            url=meta.get("url"),
            snippet=chunk["content"][:200],
            provider=meta.get("provider", "unknown"),
            author_name=meta.get("author_name"),
            relevance_score=chunk.get("score", 0.0),
        ))

        # Aggregate people
        author = meta.get("author_name") or meta.get("author_email")
        if author:
            key = author.lower()
            if key not in people:
                people[key] = {
                    "name": meta.get("author_name"),
                    "email": meta.get("author_email"),
                    "count": 0,
                    "providers": set(),
                }
            people[key]["count"] += 1
            people[key]["providers"].add(meta.get("provider", "unknown"))

    people_list = [
        PersonOverlap(
            name=p["name"],
            email=p["email"],
            overlap_count=p["count"],
            providers=list(p["providers"]),
        )
        for p in sorted(people.values(), key=lambda x: x["count"], reverse=True)
    ]

    # Generate draft message and summary using LLM
    draft_message = ""
    summary = ""
    if chunks:
        client = get_openai()
        messages = build_scan_prompt(content=req.content, chunks=chunks)
        response = await with_backoff(
            client.chat.completions.create,
            model=settings.llm_model,
            messages=messages,
            temperature=0.3,
        )
        llm_output = response.choices[0].message.content or ""

        # Parse LLM output - expects SUMMARY: and DRAFT: sections
        if "DRAFT:" in llm_output:
            parts = llm_output.split("DRAFT:", 1)
            summary = parts[0].replace("SUMMARY:", "").strip()
            draft_message = parts[1].strip()
        else:
            summary = llm_output.strip()
            draft_message = f"Hey team, I'm working on something related to: {req.content[:100]}. Looks like some of you have touched similar areas. Want to sync up?"

    return ScanResponse(
        overlaps=overlaps,
        people=people_list,
        draft_message=draft_message,
        summary=summary,
    )
