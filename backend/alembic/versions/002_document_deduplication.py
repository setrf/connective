"""document deduplication with document_access table

Revision ID: 002
Revises: 001
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create document_access table
    op.create_table(
        "document_access",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.UniqueConstraint(
            "user_id", "document_id", name="uq_document_access_user_doc"
        ),
    )

    # 2. Backfill: every existing document gets an access entry for its owner
    op.execute(
        "INSERT INTO document_access (id, user_id, document_id) "
        "SELECT gen_random_uuid(), user_id, id FROM documents"
    )

    # 3. Change documents unique constraint from (user_id, provider, external_id)
    #    to (provider, external_id) for global dedup
    op.drop_constraint(
        "uq_documents_user_provider_external", "documents", type_="unique"
    )
    op.create_unique_constraint(
        "uq_documents_provider_external",
        "documents",
        ["provider", "external_id"],
    )


def downgrade() -> None:
    # Restore old unique constraint
    op.drop_constraint(
        "uq_documents_provider_external", "documents", type_="unique"
    )
    op.create_unique_constraint(
        "uq_documents_user_provider_external",
        "documents",
        ["user_id", "provider", "external_id"],
    )

    op.drop_table("document_access")
