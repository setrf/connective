import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Column, Field, Index, SQLModel, text


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    role: str = Field(sa_column=Column(sa.Text, nullable=False))  # user|assistant|system
    content: str = Field(sa_column=Column(sa.Text, nullable=False))
    citations: list | None = Field(default=None, sa_column=Column(JSONB))
    confidence: float | None = Field(default=None, sa_column=Column(sa.Float))
    metadata_: dict | None = Field(
        default=None, sa_column=Column("metadata", JSONB)
    )
    created_at: datetime.datetime = Field(
        sa_column=Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )

    __table_args__ = (
        Index("ix_chat_messages_user_created", "user_id", "created_at"),
    )
