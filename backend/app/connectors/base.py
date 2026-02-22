import datetime
from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Base class for all integration connectors."""

    @abstractmethod
    def get_oauth_url(self, user_id: str) -> str:
        """Return the OAuth authorization URL."""
        ...

    @abstractmethod
    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange an OAuth code for tokens. Returns dict with access_token, refresh_token, scopes, expires_at, extra_data."""
        ...

    @abstractmethod
    async def validate_token(self, access_token: str) -> bool:
        """Check if the token is still valid."""
        ...

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh the access token. Returns dict with new access_token, expires_at."""
        ...

    @abstractmethod
    async def fetch_documents(
        self,
        access_token: str,
        config: dict,
        since: datetime.datetime,
        cursor: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch documents from the source. Returns list of document dicts."""
        ...
