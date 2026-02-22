import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Column, Field, Index, SQLModel, text


class OverlapAlert(SQLModel, table=True):
    __tablename__ = "overlap_alerts"

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
    doc_a_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    doc_b_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    similarity_score: float = Field(sa_column=Column(sa.Float, nullable=False))
    summary: str | None = Field(default=None, sa_column=Column(sa.Text))
    other_user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    is_read: bool = Field(
        default=False, sa_column=Column(sa.Boolean, nullable=False, server_default=text("false"))
    )
    chat_message_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="SET NULL"),
        ),
    )
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
        sa.UniqueConstraint("doc_a_id", "doc_b_id", name="uq_overlap_alerts_doc_pair"),
        Index("ix_overlap_alerts_user_read", "user_id", "is_read"),
    )
