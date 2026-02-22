import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Column, Field, SQLModel, text


class Document(SQLModel, table=True):
    __tablename__ = "documents"

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
            index=True,
        ),
    )
    connector_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    provider: str = Field(sa_column=Column(sa.Text, nullable=False))
    external_id: str = Field(sa_column=Column(sa.Text, nullable=False))
    title: str | None = Field(default=None, sa_column=Column(sa.Text))
    url: str | None = Field(default=None, sa_column=Column(sa.Text))
    author_name: str | None = Field(default=None, sa_column=Column(sa.Text))
    author_email: str | None = Field(default=None, sa_column=Column(sa.Text))
    content_type: str = Field(sa_column=Column(sa.Text, nullable=False))
    raw_content: str | None = Field(default=None, sa_column=Column(sa.Text))
    metadata_: dict | None = Field(
        default=None, sa_column=Column("metadata", JSONB)
    )
    source_created_at: datetime.datetime | None = Field(
        default=None, sa_column=Column(sa.DateTime(timezone=True))
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "provider", "external_id",
            name="uq_documents_provider_external",
        ),
    )
