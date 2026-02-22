import asyncio
import logging
import random

from openai import (
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.config import settings

logger = logging.getLogger("uvicorn.error")

_client: AsyncOpenAI | None = None

MAX_RETRIES = 11
BASE_DELAY = 2.0
MAX_RETRY_TIME = 30.0


def get_openai() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def with_backoff(fn, *args, **kwargs):
    """Retry wrapper with exponential backoff (from ethelflow pattern)."""
    for attempt in range(MAX_RETRIES):
        try:
            return await fn(*args, **kwargs)
        except (RateLimitError, APITimeoutError, APIError) as e:
            status_code = getattr(e, "status_code", None)
            if status_code not in (429, 500, 503):
                raise

            backoff_delay = BASE_DELAY * (2**attempt) + random.uniform(0, 0.5)
            delay = min(backoff_delay, MAX_RETRY_TIME)

            if attempt == MAX_RETRIES - 1:
                raise

            logger.warning(
                f"Rate limit or transient error (HTTP {status_code}), "
                f"retrying in {delay:.2f}s (attempt {attempt + 1}/{MAX_RETRIES})..."
            )
            await asyncio.sleep(delay)
        except Exception:
            raise
