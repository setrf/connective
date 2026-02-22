import datetime
import uuid

from pydantic import BaseModel


class OverlapAlertOut(BaseModel):
    id: uuid.UUID
    summary: str | None
    similarity_score: float
    is_read: bool
    other_user_name: str | None
    other_user_email: str | None
    doc_a_title: str | None
    doc_a_provider: str | None
    doc_a_url: str | None
    doc_b_title: str | None
    doc_b_provider: str | None
    doc_b_url: str | None
    chat_message_id: uuid.UUID | None
    created_at: datetime.datetime


class NotificationsResponse(BaseModel):
    alerts: list[OverlapAlertOut]
    unread_count: int


class MarkReadRequest(BaseModel):
    alert_ids: list[uuid.UUID]
