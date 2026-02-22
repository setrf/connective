import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    filters: dict | None = None  # {providers: [], date_from, date_to}


class Citation(BaseModel):
    index: int
    title: str | None
    url: str | None
    snippet: str
    author_name: str | None
    provider: str
    source_created_at: datetime.datetime | None
    metadata: dict | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float | None = None
