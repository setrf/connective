import datetime
import uuid

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
    user_message_id: str | None = None
    assistant_message_id: str | None = None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: list | None = None
    confidence: float | None = None
    metadata: dict | None = None
    created_at: datetime.datetime


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]
    has_more: bool
