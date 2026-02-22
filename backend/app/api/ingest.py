import asyncio
import datetime
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.connectors import get_connector
from app.database import get_session_ctx
from app.models.connector import Connector
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.pipeline.indexer import cleanup_stale_documents, index_documents
from app.schemas.connector import IngestStatusResponse
from app.services.encryption import decrypt_token, encrypt_token

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


async def _run_ingestion(user_id: str, provider: str):
    """Background task to fetch and index documents from a connector."""
    import uuid

    async with get_session_ctx() as db:
        uid = uuid.UUID(user_id)

        # Get connector and token
        result = await db.execute(
            select(Connector).where(
                Connector.user_id == uid,
                Connector.provider == provider,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            logger.error(f"Connector not found for {provider}/{user_id}")
            return

        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == uid,
                OAuthToken.provider == provider,
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            conn.status = "error"
            conn.error_message = "No OAuth token found"
            await db.commit()
            return

        # Skip GitHub connectors with no repos configured
        if provider == "github" and not (conn.config or {}).get("repos"):
            logger.info(f"Skipping GitHub sync for {user_id} — no repos configured")
            return

        # Skip Google Drive connectors with no folders configured
        if provider == "google_drive" and not (conn.config or {}).get("folders"):
            logger.info(f"Skipping Google Drive sync for {user_id} — no folders configured")
            return

        conn.status = "syncing"
        await db.commit()

        try:
            access_token = decrypt_token(token.access_token)
            connector_impl = get_connector(provider)

            # Refresh token if expired
            if (
                token.expires_at
                and token.expires_at < datetime.datetime.now(datetime.UTC)
                and token.refresh_token
            ):
                logger.info(f"Refreshing expired token for {provider}/{user_id}")
                refresh_tok = decrypt_token(token.refresh_token)
                new_data = await connector_impl.refresh_access_token(refresh_tok)
                access_token = new_data["access_token"]
                token.access_token = encrypt_token(access_token)
                if new_data.get("expires_at"):
                    token.expires_at = new_data["expires_at"]
                await db.commit()

            # Fetch documents (last 90 days)
            since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=90)
            documents = await connector_impl.fetch_documents(
                access_token=access_token,
                config=conn.config or {},
                since=since,
                cursor=conn.sync_cursor,
            )

            # Index the documents
            new_docs = await index_documents(
                db=db,
                user_id=uid,
                connector_id=conn.id,
                provider=provider,
                documents=documents,
            )

            # Clean up stale documents not returned by this fetch
            try:
                fetched_external_ids = {doc["external_id"] for doc in documents}
                await cleanup_stale_documents(
                    db=db,
                    user_id=uid,
                    provider=provider,
                    fetched_external_ids=fetched_external_ids,
                    since=since,
                )
            except Exception:
                logger.exception(
                    f"Stale document cleanup failed for {provider}/{user_id}"
                )
                await db.rollback()

            # Run overlap detection for newly indexed documents
            if new_docs:
                from app.pipeline.overlap_detector import detect_overlaps_for_document

                for new_doc in new_docs:
                    try:
                        await detect_overlaps_for_document(
                            db=db,
                            document_id=new_doc["document_id"],
                            user_id=uid,
                            chunk_embeddings=new_doc["chunk_embeddings"],
                        )
                    except Exception:
                        logger.exception(
                            f"Overlap detection failed for doc {new_doc['document_id']}"
                        )
                await db.commit()

            conn.status = "ready"
            conn.last_synced_at = datetime.datetime.now(datetime.UTC)
            conn.error_message = None
            await db.commit()

            logger.info(
                f"Ingestion complete for {provider}/{user_id}: "
                f"{len(documents)} documents"
            )

        except Exception as e:
            logger.exception(f"Ingestion failed for {provider}/{user_id}")
            try:
                await db.rollback()
                # Re-fetch connector after rollback (previous object is expired)
                result = await db.execute(
                    select(Connector).where(
                        Connector.user_id == uid,
                        Connector.provider == provider,
                    )
                )
                conn = result.scalar_one_or_none()
                if conn:
                    conn.status = "error"
                    conn.error_message = str(e)[:500]
                    await db.commit()
            except Exception:
                logger.exception(
                    f"Failed to update error status for {provider}/{user_id}"
                )


@router.post("/{provider}/trigger")
async def trigger_ingest(
    provider: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check connector exists and is connected
    result = await db.execute(
        select(Connector).where(
            Connector.user_id == user.id,
            Connector.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn or conn.status == "disconnected":
        raise HTTPException(status_code=400, detail="Connector not connected")

    if conn.status == "syncing":
        raise HTTPException(status_code=409, detail="Sync already in progress")

    if provider == "github" and not (conn.config or {}).get("repos"):
        raise HTTPException(
            status_code=400,
            detail="No repos configured — select repos before syncing",
        )

    if provider == "google_drive" and not (conn.config or {}).get("folders"):
        raise HTTPException(
            status_code=400,
            detail="No folders configured — select folders before syncing",
        )

    background_tasks.add_task(_run_ingestion, str(user.id), provider)
    return {"status": "started"}


@router.get("/{provider}/status", response_model=IngestStatusResponse)
async def ingest_status(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Connector).where(
            Connector.user_id == user.id,
            Connector.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return IngestStatusResponse(
            provider=provider,
            status="disconnected",
            last_synced_at=None,
            error_message=None,
        )
    return IngestStatusResponse(
        provider=provider,
        status=conn.status,
        last_synced_at=conn.last_synced_at,
        error_message=conn.error_message,
    )
