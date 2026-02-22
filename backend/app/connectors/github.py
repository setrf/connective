import datetime
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.connectors.base import BaseConnector

logger = logging.getLogger("uvicorn.error")

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"

SCOPES = "repo,read:user,user:email"


class GitHubConnector(BaseConnector):
    def get_oauth_url(self, user_id: str) -> str:
        params = {
            "client_id": settings.github_client_id,
            "scope": SCOPES,
            "redirect_uri": f"{settings.backend_url}/api/connectors/github/callback",
            "state": user_id,
        }
        return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            data = resp.json()

        if "error" in data:
            raise ValueError(f"GitHub OAuth failed: {data['error_description']}")

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "scopes": data.get("scope", "").split(","),
            "expires_at": None,
            "extra_data": {},
        }

    async def validate_token(self, access_token: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return resp.status_code == 200

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        raise NotImplementedError("GitHub OAuth tokens don't expire")

    async def fetch_documents(
        self,
        access_token: str,
        config: dict,
        since: datetime.datetime,
        cursor: dict | None = None,
    ) -> list[dict[str, Any]]:
        documents = []
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            # Get user's repos
            repos_resp = await client.get(
                f"{GITHUB_API_BASE}/user/repos",
                headers=headers,
                params={"sort": "updated", "per_page": 100},
            )
            repos = repos_resp.json()

            selected_repos = config.get("repos")
            if not selected_repos:
                logger.info("No repos configured for GitHub — skipping sync")
                return documents

            since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

            for repo in repos:
                if repo["full_name"] not in selected_repos:
                    continue

                repo_name = repo["full_name"]

                # Fetch issues
                page = 1
                while True:
                    resp = await client.get(
                        f"{GITHUB_API_BASE}/repos/{repo_name}/issues",
                        headers=headers,
                        params={
                            "since": since_iso,
                            "state": "all",
                            "per_page": 100,
                            "page": page,
                        },
                    )
                    issues = resp.json()
                    if not issues:
                        break

                    for issue in issues:
                        # Skip pull requests in issues endpoint
                        if issue.get("pull_request"):
                            continue

                        body = issue.get("body") or ""
                        documents.append({
                            "external_id": f"github:issue:{repo_name}:{issue['number']}",
                            "title": f"{repo_name}#{issue['number']}: {issue['title']}",
                            "url": issue["html_url"],
                            "author_name": issue["user"]["login"],
                            "content_type": "issue",
                            "raw_content": f"{issue['title']}\n\n{body}",
                            "metadata": {
                                "repo": repo_name,
                                "number": issue["number"],
                                "state": issue["state"],
                                "labels": [l["name"] for l in issue.get("labels", [])],
                            },
                            "source_created_at": issue["created_at"],
                        })

                    page += 1

                # Fetch PRs
                page = 1
                while True:
                    resp = await client.get(
                        f"{GITHUB_API_BASE}/repos/{repo_name}/pulls",
                        headers=headers,
                        params={
                            "state": "all",
                            "sort": "updated",
                            "direction": "desc",
                            "per_page": 100,
                            "page": page,
                        },
                    )
                    prs = resp.json()
                    if not prs:
                        break

                    for pr in prs:
                        updated = datetime.datetime.fromisoformat(
                            pr["updated_at"].replace("Z", "+00:00")
                        )
                        if updated < since:
                            break

                        body = pr.get("body") or ""
                        documents.append({
                            "external_id": f"github:pr:{repo_name}:{pr['number']}",
                            "title": f"{repo_name}#{pr['number']}: {pr['title']}",
                            "url": pr["html_url"],
                            "author_name": pr["user"]["login"],
                            "content_type": "pr",
                            "raw_content": f"{pr['title']}\n\n{body}",
                            "metadata": {
                                "repo": repo_name,
                                "number": pr["number"],
                                "state": pr["state"],
                                "merged": pr.get("merged_at") is not None,
                            },
                            "source_created_at": pr["created_at"],
                        })

                    page += 1

                # Fetch recent commits
                resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{repo_name}/commits",
                    headers=headers,
                    params={"since": since_iso, "per_page": 100},
                )
                commits = resp.json()

                for commit in commits:
                    msg = commit["commit"]["message"]
                    author = commit["commit"]["author"]
                    documents.append({
                        "external_id": f"github:commit:{repo_name}:{commit['sha']}",
                        "title": f"{repo_name}: {msg.split(chr(10))[0][:80]}",
                        "url": commit["html_url"],
                        "author_name": author.get("name", "unknown"),
                        "author_email": author.get("email"),
                        "content_type": "commit",
                        "raw_content": msg,
                        "metadata": {"repo": repo_name, "sha": commit["sha"]},
                        "source_created_at": author.get("date"),
                    })

        logger.info(f"Fetched {len(documents)} items from GitHub")
        return documents
