import asyncio
import datetime
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.connectors.base import BaseConnector

logger = logging.getLogger("uvicorn.error")

SLACK_AUTH_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_API_BASE = "https://slack.com/api"

USER_SCOPES = "channels:history,channels:read,groups:history,groups:read,users:read"


class SlackConnector(BaseConnector):
    def get_oauth_url(self, user_id: str) -> str:
        params = {
            "client_id": settings.slack_client_id,
            "user_scope": USER_SCOPES,
            "redirect_uri": f"{settings.backend_url}/api/connectors/slack/callback",
            "state": user_id,
        }
        return f"{SLACK_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SLACK_TOKEN_URL,
                data={
                    "client_id": settings.slack_client_id,
                    "client_secret": settings.slack_client_secret,
                    "code": code,
                },
            )
            data = resp.json()

        if not data.get("ok"):
            raise ValueError(f"Slack OAuth failed: {data.get('error')}")

        # User token is nested under authed_user for user_scope flows
        authed_user = data.get("authed_user", {})
        access_token = authed_user.get("access_token") or data.get("access_token")

        return {
            "access_token": access_token,
            "refresh_token": authed_user.get("refresh_token"),
            "scopes": authed_user.get("scope", "").split(","),
            "expires_at": None,
            "extra_data": {"team_id": data.get("team", {}).get("id")},
        }

    async def validate_token(self, access_token: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SLACK_API_BASE}/auth.test",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return resp.json().get("ok", False)

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        # Slack bot tokens don't expire, but user tokens may
        raise NotImplementedError("Slack tokens typically don't need refresh")

    async def _resolve_user_names(
        self, client: httpx.AsyncClient, headers: dict, user_ids: set[str]
    ) -> dict[str, str]:
        """Resolve Slack user IDs to display names via users.info."""
        names: dict[str, str] = {}
        for uid in user_ids:
            try:
                resp = await client.get(
                    f"{SLACK_API_BASE}/users.info",
                    headers=headers,
                    params={"user": uid},
                )
                data = resp.json()
                if data.get("ok"):
                    user = data["user"]
                    names[uid] = (
                        user.get("real_name")
                        or user.get("profile", {}).get("display_name")
                        or user.get("name", uid)
                    )
                else:
                    names[uid] = uid
                await asyncio.sleep(0.5)  # Rate limit courtesy
            except Exception:
                names[uid] = uid
        return names

    async def fetch_documents(
        self,
        access_token: str,
        config: dict,
        since: datetime.datetime,
        cursor: dict | None = None,
    ) -> list[dict[str, Any]]:
        documents = []
        user_ids: set[str] = set()
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            # Get channels
            channels_resp = await client.get(
                f"{SLACK_API_BASE}/conversations.list",
                headers=headers,
                params={"types": "public_channel", "limit": 200},
            )
            channels = channels_resp.json().get("channels", [])

            selected_channels = config.get("channels")

            for channel in channels:
                if selected_channels and channel["id"] not in selected_channels:
                    continue

                # Fetch channel history
                oldest = str(since.timestamp())
                history_cursor = None

                while True:
                    params = {
                        "channel": channel["id"],
                        "oldest": oldest,
                        "limit": 200,
                    }
                    if history_cursor:
                        params["cursor"] = history_cursor

                    resp = await client.get(
                        f"{SLACK_API_BASE}/conversations.history",
                        headers=headers,
                        params=params,
                    )
                    data = resp.json()

                    if not data.get("ok"):
                        # Handle rate limiting
                        if data.get("error") == "ratelimited":
                            retry_after = int(
                                resp.headers.get("Retry-After", "5")
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        logger.warning(
                            f"Slack API error for {channel['name']}: {data.get('error')}"
                        )
                        break

                    for msg in data.get("messages", []):
                        if msg.get("subtype"):
                            continue  # Skip system messages

                        uid = msg.get("user", "unknown")
                        user_ids.add(uid)
                        ts = float(msg["ts"])
                        documents.append({
                            "external_id": f"slack:{channel['id']}:{msg['ts']}",
                            "title": f"#{channel['name']}",
                            "url": f"https://slack.com/archives/{channel['id']}/p{msg['ts'].replace('.', '')}",
                            "author_name": uid,  # Placeholder, resolved below
                            "content_type": "message",
                            "raw_content": msg.get("text", ""),
                            "metadata": {
                                "channel_id": channel["id"],
                                "channel_name": channel["name"],
                                "thread_ts": msg.get("thread_ts"),
                                "reply_count": msg.get("reply_count", 0),
                            },
                            "source_created_at": datetime.datetime.fromtimestamp(
                                ts, tz=datetime.UTC
                            ).isoformat(),
                        })

                    if not data.get("has_more"):
                        break
                    history_cursor = data.get("response_metadata", {}).get(
                        "next_cursor"
                    )

                # Be nice to the Slack API
                await asyncio.sleep(1)

            # Resolve user IDs to display names
            if user_ids:
                names = await self._resolve_user_names(client, headers, user_ids)
                for doc in documents:
                    doc["author_name"] = names.get(
                        doc["author_name"], doc["author_name"]
                    )

        logger.info(f"Fetched {len(documents)} messages from Slack")
        return documents
