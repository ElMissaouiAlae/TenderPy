"""widen tender_object column

Revision ID: 51f9effca94c
Revises: 001
Create Date: 2026-08-19 19:42:55.710633

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '51f9effca94c'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "tender_records",
        "tender_object",
        type_=sa.String(),
        existing_type=sa.String(length=1000),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tender_records",
        "tender_object",
        type_=sa.String(length=1000),
        existing_type=sa.String(),
        existing_nullable=True,
    )
