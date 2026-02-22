import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, UUID as PGUUID
from sqlmodel import Column, Field, SQLModel, text


class OAuthToken(SQLModel, table=True):
    __tablename__ = "oauth_tokens"

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
    access_token: bytes = Field(sa_column=Column(BYTEA, nullable=False))
    refresh_token: bytes | None = Field(default=None, sa_column=Column(BYTEA))
    scopes: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(sa.Text))
    )
    expires_at: datetime.datetime | None = Field(
        default=None, sa_column=Column(sa.DateTime(timezone=True))
    )
    extra_data: dict | None = Field(default=None, sa_column=Column(JSONB))

    __table_args__ = (
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_tokens_user_provider"),
    )
