"""add dce_files and chunks with pgvector embeddings

Also moves tenders the old flow marked INDEXED straight after upload back to
UPLOADED, so INDEXED only ever means "chunks embedded and searchable".

Revision ID: 420f5d920afe
Revises: 1b424ba1224b
Create Date: 2026-10-07 17:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '420f5d920afe'
down_revision: Union[str, None] = '1b424ba1224b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match EMBEDDING_DIM; changing the model means a new migration (ADR 0001).
EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "dce_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tender_record_id",
            sa.Integer(),
            sa.ForeignKey("tender_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dce_files_tender_record_id", "dce_files", ["tender_record_id"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dce_file_id",
            sa.Integer(),
            sa.ForeignKey("dce_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_numbers", sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column("heading_path", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("embedding_model", sa.String(length=200), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("dce_file_id", "chunk_index", name="uq_chunks_dce_file_chunk_index"),
    )
    op.create_index("ix_chunks_dce_file_id", "chunks", ["dce_file_id"])
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.execute("UPDATE tender_records SET status = 'UPLOADED' WHERE status = 'INDEXED'")


def downgrade() -> None:
    # Under the old flow INDEXED was set right after upload, so every tender
    # that reached UPLOADED or an indexing step maps back to INDEXED.
    op.execute(
        "UPDATE tender_records SET status = 'INDEXED' "
        "WHERE status IN ('UPLOADED', 'CHUNKING', 'CHUNKED', 'EMBEDDING')"
    )
    op.execute(
        "UPDATE tender_records SET last_status = 'UPLOADED' "
        "WHERE last_status IN ('CHUNKING', 'CHUNKED', 'EMBEDDING')"
    )

    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_dce_file_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_dce_files_tender_record_id", table_name="dce_files")
    op.drop_table("dce_files")
    # The vector extension is left installed: other objects may depend on it.
