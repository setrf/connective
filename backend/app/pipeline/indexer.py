import datetime
import logging
import uuid

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
):
    """Process and index a list of documents: preprocess, chunk, embed, store.

    Documents are globally deduplicated by (provider, external_id).
    If a document already exists (synced by another user), we skip
    re-embedding and just grant the current user access via document_access.
    """
    new_count = 0
    dedup_count = 0

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

    await db.commit()
    logger.info(
        f"Indexed {provider}: {new_count} new, {dedup_count} deduplicated "
        f"(of {len(documents)} total)"
    )
