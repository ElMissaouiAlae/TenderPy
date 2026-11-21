"""Initial migration creating tender_records table.

Revision ID: 001
Revises: 
Create Date: 2026-08-01 19:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tender_records table with indexes and constraints."""
    op.create_table(
        "tender_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tender_id", sa.String(length=50), nullable=True),
        sa.Column("organization_acronym", sa.String(length=50), nullable=True),
        sa.Column("procurement_type", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("publication_date", sa.String(length=20), nullable=True),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("tender_object", sa.String(length=1000), nullable=True),
        sa.Column("public_buyer", sa.String(length=500), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("tender_end_date", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DISCOVERED"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tender_records_tender_id"), "tender_records", ["tender_id"], unique=False)
    op.create_index(
        op.f("ix_tender_records_organization_acronym"), "tender_records", ["organization_acronym"], unique=False
    )
    op.create_index(
        op.f("ix_tender_records_publication_date"), "tender_records", ["publication_date"], unique=False
    )
    op.create_index(op.f("ix_tender_records_status"), "tender_records", ["status"], unique=False)
    op.create_index(
        op.f("ix_tender_records_tender_id_org_acronym"),
        "tender_records",
        ["tender_id", "organization_acronym"],
        unique=True,
    )


def downgrade() -> None:
    """Drop tender_records table and indexes."""
    op.drop_index(op.f("ix_tender_records_tender_id_org_acronym"), table_name="tender_records")
    op.drop_index(op.f("ix_tender_records_status"), table_name="tender_records")
    op.drop_index(op.f("ix_tender_records_publication_date"), table_name="tender_records")
    op.drop_index(op.f("ix_tender_records_organization_acronym"), table_name="tender_records")
    op.drop_index(op.f("ix_tender_records_tender_id"), table_name="tender_records")
    op.drop_table("tender_records")
