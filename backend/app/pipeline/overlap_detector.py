import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.overlap_alert import OverlapAlert
from app.models.user import User
from app.pipeline.retriever import cross_user_similarity_search
from app.prompts.overlap_confirm import build_overlap_confirm_prompt
from app.services.openai_client import get_openai, with_backoff

logger = logging.getLogger("uvicorn.error")


def _canonicalize_pair(
    doc_a_id: uuid.UUID, doc_b_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """Sort UUIDs so the smaller one comes first for consistent dedup."""
    if str(doc_a_id) < str(doc_b_id):
        return doc_a_id, doc_b_id
    return doc_b_id, doc_a_id


async def _pair_already_alerted(
    db: AsyncSession, doc_a_id: uuid.UUID, doc_b_id: uuid.UUID
) -> bool:
    """Check if this document pair has already triggered an alert."""
    canon_a, canon_b = _canonicalize_pair(doc_a_id, doc_b_id)
    result = await db.execute(
        select(OverlapAlert.id).where(
            OverlapAlert.doc_a_id == canon_a,
            OverlapAlert.doc_b_id == canon_b,
        )
    )
    return result.scalar_one_or_none() is not None


async def _llm_confirm_overlap(
    source_doc: Document,
    source_preview: str,
    target_title: str | None,
    target_provider: str | None,
    target_author: str | None,
    target_preview: str,
) -> dict | None:
    """Use LLM to confirm overlap and get a summary. Returns None if below threshold."""
    messages = build_overlap_confirm_prompt(
        source_title=source_doc.title,
        source_provider=source_doc.provider,
        source_author=source_doc.author_name,
        source_preview=source_preview,
        target_title=target_title,
        target_provider=target_provider,
        target_author=target_author,
        target_preview=target_preview,
    )

    client = get_openai()
    response = await with_backoff(
        client.chat.completions.create,
        model=settings.llm_model,
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        content = response.choices[0].message.content or "{}"
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(content)
        confidence = float(result.get("confidence", 0.0))
        summary = result.get("summary", "")

        if confidence >= settings.overlap_llm_confirm_threshold:
            return {"confidence": confidence, "summary": summary}
        return None
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as e:
        logger.warning(f"LLM overlap confirmation failed to parse: {e}")
        return None


def _build_system_message(
    source_doc: Document,
    target_doc: Document,
    other_user: User,
    summary: str,
) -> str:
    """Build human-readable overlap alert message."""
    lines = []
    lines.append(f"Your work: [{source_doc.provider}] {source_doc.title or 'Untitled'}")
    other_name = other_user.name or other_user.email
    lines.append(
        f"Similar work by {other_name}: [{target_doc.provider}] {target_doc.title or 'Untitled'}"
    )
    if target_doc.url:
        lines.append(f"Link: {target_doc.url}")
    lines.append("")
    lines.append(summary)
    lines.append("")
    lines.append("Consider reaching out to coordinate.")
    return "\n".join(lines)


async def detect_overlaps_for_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    chunk_embeddings: list[list[float]],
) -> None:
    """Detect overlaps between a newly indexed document and other users' documents.

    For each candidate:
    1. Check dedup (canonical pair)
    2. LLM confirm
    3. Determine recipient (later source_created_at gets notified)
    4. Create ChatMessage + OverlapAlert
    """
    if not settings.overlap_detection_enabled:
        logger.debug("Overlap detection disabled, skipping")
        return

    if not chunk_embeddings:
        logger.warning(f"Overlap detection for doc {document_id}: no embeddings, skipping")
        return

    # Get the source document
    result = await db.execute(select(Document).where(Document.id == document_id))
    source_doc = result.scalar_one_or_none()
    if not source_doc:
        logger.warning(f"Overlap detection: source doc {document_id} not found")
        return

    # Find similar documents across other users
    candidates = await cross_user_similarity_search(
        db=db,
        source_user_id=user_id,
        source_document_id=document_id,
        chunk_embeddings=chunk_embeddings,
        similarity_threshold=settings.overlap_similarity_threshold,
    )

    if not candidates:
        return

    logger.info(
        f"Overlap detection for doc {document_id}: {len(candidates)} candidates"
    )

    for candidate in candidates:
        target_doc_id = candidate["document_id"]
        canon_a, canon_b = _canonicalize_pair(document_id, target_doc_id)

        # Skip if already alerted
        if await _pair_already_alerted(db, canon_a, canon_b):
            continue

        # Get target document
        result = await db.execute(select(Document).where(Document.id == target_doc_id))
        target_doc = result.scalar_one_or_none()
        if not target_doc:
            continue

        # LLM confirm
        target_meta = candidate.get("chunk_metadata", {}) or {}
        llm_result = await _llm_confirm_overlap(
            source_doc=source_doc,
            source_preview=source_doc.raw_content[:1000] if source_doc.raw_content else "",
            target_title=target_doc.title,
            target_provider=target_doc.provider,
            target_author=target_meta.get("author_name"),
            target_preview=candidate.get("chunk_content", ""),
        )

        if not llm_result:
            continue

        # Determine recipient: later doc's user gets notified
        # Default: notify the source user (who just synced)
        notify_user_id = user_id
        other_user_id = target_doc.user_id
        notified_doc = source_doc
        other_doc = target_doc

        if (
            source_doc.source_created_at
            and target_doc.source_created_at
            and source_doc.source_created_at < target_doc.source_created_at
        ):
            # Target doc is newer — notify target doc's user instead
            notify_user_id = target_doc.user_id
            other_user_id = user_id
            notified_doc = target_doc
            other_doc = source_doc

        # Get the other user's info for the message
        result = await db.execute(select(User).where(User.id == other_user_id))
        other_user = result.scalar_one_or_none()
        if not other_user:
            continue

        # Build system message content
        message_content = _build_system_message(
            source_doc=notified_doc,
            target_doc=other_doc,
            other_user=other_user,
            summary=llm_result["summary"],
        )

        # Create chat message
        chat_msg = ChatMessage(
            user_id=notify_user_id,
            role="system",
            content=message_content,
            metadata_={
                "type": "overlap_alert",
                "doc_a_id": str(canon_a),
                "doc_b_id": str(canon_b),
                "other_user_id": str(other_user_id),
                "other_user_name": other_user.name,
                "similarity_score": llm_result["confidence"],
            },
        )
        db.add(chat_msg)
        await db.flush()

        # Create overlap alert
        alert = OverlapAlert(
            user_id=notify_user_id,
            doc_a_id=canon_a,
            doc_b_id=canon_b,
            similarity_score=llm_result["confidence"],
            summary=llm_result["summary"],
            other_user_id=other_user_id,
            chat_message_id=chat_msg.id,
            metadata_={
                "doc_a_title": source_doc.title if canon_a == document_id else target_doc.title,
                "doc_a_provider": source_doc.provider if canon_a == document_id else target_doc.provider,
                "doc_a_url": source_doc.url if canon_a == document_id else target_doc.url,
                "doc_b_title": target_doc.title if canon_a == document_id else source_doc.title,
                "doc_b_provider": target_doc.provider if canon_a == document_id else source_doc.provider,
                "doc_b_url": target_doc.url if canon_a == document_id else source_doc.url,
            },
        )
        db.add(alert)

        logger.info(
            f"Overlap alert created: {canon_a} <-> {canon_b} "
            f"(confidence={llm_result['confidence']:.2f}, notify={notify_user_id})"
        )
