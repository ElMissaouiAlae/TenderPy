"""typed publication date and deadline

publication_date becomes a DATE and tender_end_date is renamed deadline and
becomes a TIMESTAMPTZ in Moroccan local time. Existing text is converted
with the same functions the parser uses (core.dates), so the rules can't
diverge. Text that can't be read becomes NULL and is logged with the
record's id; it never fails the migration.

The downgrade writes the typed values back as the platform's text:
DD/MM/YYYY and DD/MM/YYYY HH:mm.

Revision ID: b5d1e8a3c9f2
Revises: 7c2e9a1d4b3f
Create Date: 2026-11-24 12:00:00.000000

"""
from __future__ import annotations

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from core.dates import (
    format_deadline,
    format_publication_date,
    parse_deadline,
    parse_publication_date,
)

# revision identifiers, used by Alembic.
revision: str = 'b5d1e8a3c9f2'
down_revision: str | None = '7c2e9a1d4b3f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A child of "alembic" so alembic.ini's logging shows it during a run.
logger = logging.getLogger("alembic.typed_dates")

TABLE = "tender_records"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("publication_day", sa.Date(), nullable=True))
    op.add_column(TABLE, sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(f"SELECT id, publication_date, tender_end_date FROM {TABLE}")
    ).all()

    ids, publication_dates, deadlines = [], [], []
    nulled_publication_dates = 0
    nulled_deadlines = 0
    for id, publication_text, deadline_text in rows:
        publication_date = parse_publication_date(publication_text)
        deadline = parse_deadline(deadline_text)
        if publication_date is None and _has_text(publication_text):
            nulled_publication_dates += 1
            logger.warning(f"Tender record {id}: unreadable publication date {publication_text!r} set to NULL")
        if deadline is None and _has_text(deadline_text):
            nulled_deadlines += 1
            logger.warning(f"Tender record {id}: unreadable deadline {deadline_text!r} set to NULL")
        ids.append(id)
        publication_dates.append(publication_date)
        deadlines.append(deadline)

    # One set-based UPDATE: a row-by-row executemany costs a round trip per row.
    connection.execute(
        sa.text(
            f"UPDATE {TABLE} AS t SET publication_day = v.publication_day, deadline = v.deadline "
            "FROM unnest(CAST(:ids AS integer[]), CAST(:publication_dates AS date[]), "
            "CAST(:deadlines AS timestamptz[])) AS v(id, publication_day, deadline) "
            "WHERE t.id = v.id"
        ),
        {"ids": ids, "publication_dates": publication_dates, "deadlines": deadlines},
    )
    logger.info(
        f"Converted dates of {len(rows)} tender records: "
        f"{nulled_publication_dates} publication dates and {nulled_deadlines} deadlines "
        "were unreadable and set to NULL"
    )

    op.drop_index("ix_tender_records_publication_date", table_name=TABLE)
    op.drop_column(TABLE, "publication_date")
    op.drop_column(TABLE, "tender_end_date")
    op.alter_column(TABLE, "publication_day", new_column_name="publication_date")
    op.create_index("ix_tender_records_publication_date", TABLE, ["publication_date"])
    op.create_index("ix_tender_records_deadline", TABLE, ["deadline"])


def downgrade() -> None:
    op.add_column(TABLE, sa.Column("publication_text", sa.String(length=20), nullable=True))
    op.add_column(TABLE, sa.Column("tender_end_date", sa.String(length=50), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text(f"SELECT id, publication_date, deadline FROM {TABLE}")).all()
    connection.execute(
        sa.text(
            f"UPDATE {TABLE} AS t SET publication_text = v.publication_text, "
            "tender_end_date = v.tender_end_date "
            "FROM unnest(CAST(:ids AS integer[]), CAST(:publication_texts AS text[]), "
            "CAST(:tender_end_dates AS text[])) AS v(id, publication_text, tender_end_date) "
            "WHERE t.id = v.id"
        ),
        {
            "ids": [id for id, _, _ in rows],
            "publication_texts": [
                format_publication_date(publication_date) if publication_date else None
                for _, publication_date, _ in rows
            ],
            "tender_end_dates": [format_deadline(deadline) if deadline else None for _, _, deadline in rows],
        },
    )

    op.drop_index("ix_tender_records_deadline", table_name=TABLE)
    op.drop_index("ix_tender_records_publication_date", table_name=TABLE)
    op.drop_column(TABLE, "deadline")
    op.drop_column(TABLE, "publication_date")
    op.alter_column(TABLE, "publication_text", new_column_name="publication_date")
    op.create_index("ix_tender_records_publication_date", TABLE, ["publication_date"])


def _has_text(text: str | None) -> bool:
    return text is not None and bool(text.strip())
