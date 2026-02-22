import datetime
import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.document_access import DocumentAccess
from app.pipeline.chunker import chunk_text
from app.pipeline.embedder import embed_texts

logger = logging.getLogger("uvicorn.error")


async def _ensure_access(
    db: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID
):
    """Add a document_access entry if one doesn't already exist."""
    result = await db.execute(
        select(DocumentAccess).where(
            DocumentAccess.user_id == user_id,
            DocumentAccess.document_id == document_id,
        )
    )
    if not result.scalar_one_or_none():
        db.add(DocumentAccess(user_id=user_id, document_id=document_id))


async def index_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    connector_id: uuid.UUID,
    provider: str,
    documents: list[dict],
) -> list[dict]:
    """Process and index a list of documents: preprocess, chunk, embed, store.

    Documents are globally deduplicated by (provider, external_id).
    If a document already exists (synced by another user), we skip
    re-embedding and just grant the current user access via document_access.

    Returns a list of newly created documents with their embeddings:
    [{document_id, chunk_embeddings}, ...]
    """
    new_count = 0
    dedup_count = 0
    new_docs = []

    for doc_data in documents:
        source_created_at = None
        if doc_data.get("source_created_at"):
            if isinstance(doc_data["source_created_at"], str):
                source_created_at = datetime.datetime.fromisoformat(
                    doc_data["source_created_at"].replace("Z", "+00:00")
                )
            else:
                source_created_at = doc_data["source_created_at"]

        # Global lookup by (provider, external_id) — not per-user
        result = await db.execute(
            select(Document).where(
                Document.provider == provider,
                Document.external_id == doc_data["external_id"],
            )
        )
        existing_doc = result.scalar_one_or_none()

        if existing_doc:
            # Document already exists — just grant access and skip embedding
            await _ensure_access(db, user_id, existing_doc.id)
            dedup_count += 1
            continue

        # New document — create it, embed, and index
        doc = Document(
            user_id=user_id,
            connector_id=connector_id,
            provider=provider,
            external_id=doc_data["external_id"],
            title=doc_data.get("title"),
            url=doc_data.get("url"),
            author_name=doc_data.get("author_name"),
            author_email=doc_data.get("author_email"),
            content_type=doc_data["content_type"],
            raw_content=doc_data.get("raw_content"),
            metadata_=doc_data.get("metadata"),
            source_created_at=source_created_at,
        )
        db.add(doc)
        await db.flush()

        # Grant access to the creator
        await _ensure_access(db, user_id, doc.id)

        # Preprocess: prepend metadata header
        raw = doc_data.get("raw_content") or ""
        header = f"[{provider}] {doc_data.get('title', '')}"
        if doc_data.get("author_name"):
            header += f" by {doc_data['author_name']}"
        text_with_header = f"{header}\n\n{raw}"

        # Chunk the text
        chunks = chunk_text(text_with_header)

        if not chunks:
            continue

        # Embed all chunks
        chunk_texts = [c["content"] for c in chunks]
        embeddings = await embed_texts(chunk_texts)

        # Build chunk metadata
        chunk_meta = {
            "title": doc_data.get("title"),
            "url": doc_data.get("url"),
            "author_name": doc_data.get("author_name"),
            "author_email": doc_data.get("author_email"),
            "provider": provider,
            "content_type": doc_data["content_type"],
            "source_created_at": doc_data.get("source_created_at"),
        }
        if doc_data.get("metadata"):
            chunk_meta.update(doc_data["metadata"])

        # Store chunks with embeddings
        for chunk_data, embedding in zip(chunks, embeddings):
            chunk = Chunk(
                document_id=doc.id,
                user_id=user_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                embedding=embedding,
                metadata_=chunk_meta,
            )
            db.add(chunk)

        new_count += 1
        new_docs.append({
            "document_id": doc.id,
            "chunk_embeddings": embeddings,
        })

    await db.commit()
    logger.info(
        f"Indexed {provider}: {new_count} new, {dedup_count} deduplicated "
        f"(of {len(documents)} total)"
    )

    return new_docs


async def cleanup_stale_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    fetched_external_ids: set[str],
    since: datetime.datetime,
) -> int:
    """Remove user access for documents that should have appeared in the fetch
    window but were not returned (deleted/trashed upstream).

    A document is stale if:
    - The user has access to it
    - It belongs to the given provider
    - Its source_created_at >= since (inside the fetch window)
    - Its external_id was NOT in the current fetch results

    Documents with NULL source_created_at or older than the window are left alone.
    Orphaned documents (no remaining access) are deleted entirely.

    Returns the number of access entries removed.
    """
    # Find stale documents: in the user's access, in the fetch window, but not fetched
    stale_q = (
        select(DocumentAccess.id, Document.id.label("doc_id"))
        .join(Document, DocumentAccess.document_id == Document.id)
        .where(
            DocumentAccess.user_id == user_id,
            Document.provider == provider,
            Document.source_created_at >= since,
            Document.external_id.notin_(fetched_external_ids),
        )
    )
    result = await db.execute(stale_q)
    stale_rows = result.all()

    if not stale_rows:
        return 0

    access_ids = [row[0] for row in stale_rows]
    stale_doc_ids = [row[1] for row in stale_rows]

    # Delete user's access entries for stale documents
    await db.execute(
        sa.delete(DocumentAccess).where(DocumentAccess.id.in_(access_ids))
    )

    # Delete orphaned documents (no remaining access entries)
    orphan_subq = (
        select(Document.id)
        .outerjoin(DocumentAccess, DocumentAccess.document_id == Document.id)
        .where(
            Document.id.in_(stale_doc_ids),
            DocumentAccess.id.is_(None),
        )
    )
    orphan_result = await db.execute(
        sa.delete(Document).where(Document.id.in_(orphan_subq))
    )
    orphan_count = orphan_result.rowcount

    logger.info(
        f"Stale cleanup {provider}: removed {len(access_ids)} access entries, "
        f"{orphan_count} orphaned documents"
    )
    return len(access_ids)
