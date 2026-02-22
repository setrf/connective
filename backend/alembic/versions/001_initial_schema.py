"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, UUID, TSVECTOR

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text()),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # OAuth tokens
    op.create_table(
        "oauth_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("access_token", BYTEA(), nullable=False),
        sa.Column("refresh_token", BYTEA()),
        sa.Column("scopes", ARRAY(sa.Text())),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("extra_data", JSONB()),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_tokens_user_provider"),
    )

    # Connectors
    op.create_table(
        "connectors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'disconnected'")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("sync_cursor", JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("config", JSONB()),
        sa.UniqueConstraint("user_id", "provider", name="uq_connectors_user_provider"),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("connector_id", UUID(as_uuid=True), sa.ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("author_name", sa.Text()),
        sa.Column("author_email", sa.Text()),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("raw_content", sa.Text()),
        sa.Column("metadata", JSONB()),
        sa.Column("source_created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "provider", "external_id", name="uq_documents_user_provider_external"),
    )

    # Chunks with pgvector and tsvector
    op.create_table(
        "chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", JSONB()),
    )

    # Add vector column
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1536)")

    # Add generated tsvector column
    op.execute(
        "ALTER TABLE chunks ADD COLUMN fts tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )

    # HNSW index on embedding with halfvec cast (ethelflow pattern)
    op.execute(
        "CREATE INDEX chunks_embedding_idx ON chunks "
        "USING hnsw ((embedding::halfvec(1536)) halfvec_cosine_ops)"
    )

    # GIN index on fts
    op.execute("CREATE INDEX chunks_fts_idx ON chunks USING gin (fts)")


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("connectors")
    op.drop_table("oauth_tokens")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
