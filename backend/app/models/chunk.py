import uuid
from typing import List

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, TSVECTOR
from sqlmodel import Column, Field, Index, SQLModel, text


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    document_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
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
    chunk_index: int = Field(sa_column=Column(sa.Integer, nullable=False))
    content: str = Field(sa_column=Column(sa.Text, nullable=False))
    token_count: int = Field(sa_column=Column(sa.Integer, nullable=False, default=0))
    embedding: List[float] | None = Field(
        default=None, sa_column=Column(Vector(1536))
    )
    fts: str | None = Field(
        default=None,
        sa_column=Column(
            TSVECTOR,
            sa.Computed("to_tsvector('english', content)", persisted=True),
        ),
    )
    metadata_: dict | None = Field(
        default=None, sa_column=Column("metadata", JSONB)
    )

    __table_args__ = (
        Index(
            "chunks_embedding_idx",
            text("(embedding::halfvec(1536)) halfvec_cosine_ops"),
            postgresql_using="hnsw",
        ),
        Index(
            "chunks_fts_idx",
            "fts",
            postgresql_using="gin",
        ),
    )
