import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Column, Field, SQLModel, text


class Connector(SQLModel, table=True):
    __tablename__ = "connectors"

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
    provider: str = Field(sa_column=Column(sa.Text, nullable=False))
    status: str = Field(
        default="disconnected",
        sa_column=Column(sa.Text, nullable=False, server_default=text("'disconnected'")),
    )
    last_synced_at: datetime.datetime | None = Field(
        default=None, sa_column=Column(sa.DateTime(timezone=True))
    )
    sync_cursor: dict | None = Field(default=None, sa_column=Column(JSONB))
    error_message: str | None = Field(default=None, sa_column=Column(sa.Text))
    config: dict | None = Field(default=None, sa_column=Column(JSONB))

    __table_args__ = (
        sa.UniqueConstraint("user_id", "provider", name="uq_connectors_user_provider"),
    )
