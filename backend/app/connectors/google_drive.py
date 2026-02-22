import datetime
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.connectors.base import BaseConnector

logger = logging.getLogger("uvicorn.error")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_API_BASE = "https://www.googleapis.com"

SCOPES = "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/userinfo.email"


class GoogleDriveConnector(BaseConnector):
    def get_oauth_url(self, user_id: str) -> str:
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": f"{settings.backend_url}/api/connectors/google_drive/callback",
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"{settings.backend_url}/api/connectors/google_drive/callback",
                },
            )
            data = resp.json()

        if "error" in data:
            raise ValueError(f"Google OAuth failed: {data.get('error_description', data['error'])}")

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
                seconds=data["expires_in"]
            )

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "scopes": data.get("scope", "").split(),
            "expires_at": expires_at,
            "extra_data": {},
        }

    async def validate_token(self, access_token: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GOOGLE_API_BASE}/oauth2/v1/tokeninfo",
                params={"access_token": access_token},
            )
            return resp.status_code == 200

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            data = resp.json()

        if "error" in data:
            raise ValueError(f"Token refresh failed: {data['error']}")

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
                seconds=data["expires_in"]
            )

        return {
            "access_token": data["access_token"],
            "expires_at": expires_at,
        }

    async def _get_all_subfolder_ids(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        folder_ids: list[str],
    ) -> set[str]:
        """Recursively discover all subfolder IDs starting from the given folder IDs."""
        all_ids = set(folder_ids)
        to_visit = list(folder_ids)

        while to_visit:
            # Build query for children of current batch
            parent_clauses = " or ".join(
                f"'{fid}' in parents" for fid in to_visit
            )
            query = (
                f"mimeType = 'application/vnd.google-apps.folder' "
                f"and ({parent_clauses}) and trashed = false"
            )
            to_visit = []
            page_token = None

            while True:
                params = {
                    "q": query,
                    "fields": "nextPageToken,files(id)",
                    "pageSize": 100,
                }
                if page_token:
                    params["pageToken"] = page_token

                resp = await client.get(
                    f"{GOOGLE_API_BASE}/drive/v3/files",
                    headers=headers,
                    params=params,
                )
                data = resp.json()

                for f in data.get("files", []):
                    if f["id"] not in all_ids:
                        all_ids.add(f["id"])
                        to_visit.append(f["id"])

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return all_ids

    async def fetch_documents(
        self,
        access_token: str,
        config: dict,
        since: datetime.datetime,
        cursor: dict | None = None,
    ) -> list[dict[str, Any]]:
        # If no folders configured, return empty (same as GitHub repos pattern)
        folders = config.get("folders")
        if not folders:
            logger.info("No folders configured for Google Drive — skipping sync")
            return []

        documents = []
        headers = {"Authorization": f"Bearer {access_token}"}

        since_rfc = since.strftime("%Y-%m-%dT%H:%M:%S")

        # Filter by mime types we can process
        supported_mimes = [
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
            "application/pdf",
        ]

        async with httpx.AsyncClient() as client:
            # Recursively discover all subfolder IDs
            folder_ids = [f["id"] for f in folders]
            all_folder_ids = await self._get_all_subfolder_ids(
                client, headers, folder_ids
            )
            logger.info(
                f"Google Drive: {len(folder_ids)} selected folders expanded "
                f"to {len(all_folder_ids)} total (including subfolders)"
            )

            # Query files within all discovered folders
            # Process in batches to avoid overly long query strings
            folder_id_list = list(all_folder_ids)
            batch_size = 50
            for i in range(0, len(folder_id_list), batch_size):
                batch = folder_id_list[i : i + batch_size]
                parent_clauses = " or ".join(
                    f"'{fid}' in parents" for fid in batch
                )
                query = (
                    f"modifiedTime > '{since_rfc}' and trashed = false "
                    f"and ({parent_clauses})"
                )

                page_token = None
                while True:
                    params = {
                        "q": query,
                        "fields": "nextPageToken,files(id,name,mimeType,webViewLink,modifiedTime,owners,createdTime)",
                        "pageSize": 100,
                        "orderBy": "modifiedTime desc",
                    }
                    if page_token:
                        params["pageToken"] = page_token

                    resp = await client.get(
                        f"{GOOGLE_API_BASE}/drive/v3/files",
                        headers=headers,
                        params=params,
                    )
                    data = resp.json()

                    for file in data.get("files", []):
                        if file["mimeType"] not in supported_mimes:
                            continue

                        # Export Google Docs as plain text
                        content = ""
                        if file["mimeType"].startswith("application/vnd.google-apps"):
                            export_mime = "text/plain"
                            export_resp = await client.get(
                                f"{GOOGLE_API_BASE}/drive/v3/files/{file['id']}/export",
                                headers=headers,
                                params={"mimeType": export_mime},
                            )
                            if export_resp.status_code == 200:
                                content = export_resp.text
                        elif file["mimeType"] == "application/pdf":
                            # Download and extract text with pymupdf
                            dl_resp = await client.get(
                                f"{GOOGLE_API_BASE}/drive/v3/files/{file['id']}",
                                headers=headers,
                                params={"alt": "media"},
                            )
                            if dl_resp.status_code == 200:
                                try:
                                    import pymupdf

                                    doc = pymupdf.open(stream=dl_resp.content, filetype="pdf")
                                    content = "\n".join(
                                        page.get_text() for page in doc
                                    )
                                    doc.close()
                                except Exception as e:
                                    logger.warning(f"PDF extraction failed for {file['name']}: {e}")
                                    continue

                        if not content.strip():
                            continue

                        owners = file.get("owners", [{}])
                        owner = owners[0] if owners else {}

                        documents.append({
                            "external_id": f"gdrive:{file['id']}",
                            "title": file["name"],
                            "url": file.get("webViewLink"),
                            "author_name": owner.get("displayName"),
                            "author_email": owner.get("emailAddress"),
                            "content_type": "file",
                            "raw_content": content,
                            "metadata": {
                                "mime_type": file["mimeType"],
                                "drive_id": file["id"],
                            },
                            "source_created_at": file.get("createdTime"),
                        })

                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break

        logger.info(f"Fetched {len(documents)} files from Google Drive")
        return documents
