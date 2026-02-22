import uuid
from urllib.parse import urlencode

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.connectors import get_connector
from app.models.connector import Connector
from app.models.document import Document
from app.models.document_access import DocumentAccess
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.schemas.connector import (
    ConnectorConfigUpdate,
    ConnectorResponse,
    GitHubRepoItem,
    GoogleDriveFolderItem,
    OAuthURLResponse,
)
from app.services.encryption import decrypt_token, encrypt_token

router = APIRouter()

PROVIDERS = ["slack", "github", "google_drive"]


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Connector).where(Connector.user_id == user.id)
    )
    connectors = result.scalars().all()

    # Return all providers, filling in defaults for unconnected ones
    existing = {c.provider: c for c in connectors}
    responses = []
    for provider in PROVIDERS:
        if provider in existing:
            c = existing[provider]
            responses.append(ConnectorResponse(
                id=c.id,
                provider=c.provider,
                status=c.status,
                last_synced_at=c.last_synced_at,
                error_message=c.error_message,
                config=c.config,
            ))
        else:
            responses.append(ConnectorResponse(
                id=uuid.uuid4(),
                provider=provider,
                status="disconnected",
                last_synced_at=None,
                error_message=None,
                config=None,
            ))
    return responses


@router.get("/{provider}/oauth-url", response_model=OAuthURLResponse)
async def get_oauth_url(
    provider: str,
    user: User = Depends(get_current_user),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    connector = get_connector(provider)
    url = connector.get_oauth_url(user_id=str(user.id))
    return OAuthURLResponse(url=url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    connector = get_connector(provider)
    token_data = await connector.exchange_code(code)

    user_id = uuid.UUID(state)

    # Store encrypted token
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
        )
    )
    existing = result.scalar_one_or_none()

    encrypted_access = encrypt_token(token_data["access_token"])
    encrypted_refresh = (
        encrypt_token(token_data["refresh_token"])
        if token_data.get("refresh_token")
        else None
    )

    if existing:
        existing.access_token = encrypted_access
        existing.refresh_token = encrypted_refresh
        existing.scopes = token_data.get("scopes")
        existing.expires_at = token_data.get("expires_at")
        existing.extra_data = token_data.get("extra_data")
    else:
        oauth_token = OAuthToken(
            user_id=user_id,
            provider=provider,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            scopes=token_data.get("scopes"),
            expires_at=token_data.get("expires_at"),
            extra_data=token_data.get("extra_data"),
        )
        db.add(oauth_token)

    # Upsert connector status
    result = await db.execute(
        select(Connector).where(
            Connector.user_id == user_id,
            Connector.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        conn.status = "connected"
        conn.error_message = None
    else:
        conn = Connector(
            user_id=user_id,
            provider=provider,
            status="connected",
        )
        db.add(conn)

    await db.commit()

    # Redirect back to frontend dashboard
    return RedirectResponse(
        url=f"{settings.frontend_url}/dashboard?connected={provider}",
        status_code=302,
    )


@router.get("/{provider}/repos", response_model=list[GitHubRepoItem])
async def list_repos(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if provider != "github":
        raise HTTPException(status_code=400, detail="Repo listing only supported for GitHub")

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == provider,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="No OAuth token found — connect GitHub first")

    access_token = decrypt_token(token.access_token)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    repos: list[dict] = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={"sort": "updated", "per_page": 100, "page": page},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch repos from GitHub")
            batch = resp.json()
            if not batch:
                break
            repos.extend(batch)
            page += 1

    return [
        GitHubRepoItem(
            full_name=r["full_name"],
            description=r.get("description"),
            private=r["private"],
            updated_at=r.get("updated_at"),
            language=r.get("language"),
            stargazers_count=r.get("stargazers_count", 0),
        )
        for r in repos
    ]


@router.get("/{provider}/folders", response_model=list[GoogleDriveFolderItem])
async def list_folders(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if provider != "google_drive":
        raise HTTPException(status_code=400, detail="Folder listing only supported for Google Drive")

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == provider,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="No OAuth token found — connect Google Drive first")

    access_token = decrypt_token(token.access_token)
    headers = {"Authorization": f"Bearer {access_token}"}

    folders: list[dict] = []
    page_token = None
    async with httpx.AsyncClient() as client:
        while True:
            params = {
                "q": "mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                "fields": "nextPageToken,files(id,name)",
                "pageSize": 100,
                "orderBy": "name",
            }
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params=params,
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch folders from Google Drive")
            data = resp.json()
            folders.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return [
        GoogleDriveFolderItem(id=f["id"], name=f["name"])
        for f in folders
    ]


@router.patch("/{provider}/config")
async def update_config(
    provider: str,
    body: ConnectorConfigUpdate,
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
        raise HTTPException(status_code=404, detail="Connector not found")
    conn.config = body.config
    await db.commit()
    return {"status": "ok", "config": conn.config}


@router.delete("/{provider}")
async def disconnect(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Delete OAuth token
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == provider,
        )
    )
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)

    # Find the connector
    result = await db.execute(
        select(Connector).where(
            Connector.user_id == user.id,
            Connector.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()

    if conn:
        # Remove this user's access to documents from this provider
        access_subq = (
            select(DocumentAccess.id)
            .join(Document, DocumentAccess.document_id == Document.id)
            .where(
                DocumentAccess.user_id == user.id,
                Document.provider == provider,
            )
        )
        await db.execute(
            sa.delete(DocumentAccess).where(DocumentAccess.id.in_(access_subq))
        )

        # Delete orphan documents owned by this connector
        # (no remaining access entries → no user needs them)
        orphan_subq = (
            select(Document.id)
            .outerjoin(DocumentAccess, DocumentAccess.document_id == Document.id)
            .where(
                Document.connector_id == conn.id,
                DocumentAccess.id.is_(None),
            )
        )
        await db.execute(
            sa.delete(Document).where(Document.id.in_(orphan_subq))
        )

        # Reset connector state
        conn.status = "disconnected"
        conn.error_message = None
        conn.config = None
        conn.last_synced_at = None
        conn.sync_cursor = None

    await db.commit()
    return {"status": "disconnected"}
