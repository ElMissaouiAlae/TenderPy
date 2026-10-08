"""drop DOWNLOADED and UPLOADING statuses

The DCE archive is fetched and saved to document storage in one step, so a
tender goes straight from DOWNLOADING to UPLOADED. Rows left on a removed
status had not proven their archive is stored, so they fall back to
DOWNLOADING; neither the status nor the last_status becomes eligible for
indexing.

Revision ID: 7c2e9a1d4b3f
Revises: 420f5d920afe
Create Date: 2026-10-08 14:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7c2e9a1d4b3f'
down_revision: Union[str, None] = '420f5d920afe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE tender_records SET status = 'DOWNLOADING' "
        "WHERE status IN ('DOWNLOADED', 'UPLOADING')"
    )
    op.execute(
        "UPDATE tender_records SET last_status = 'DOWNLOADING' "
        "WHERE last_status IN ('DOWNLOADED', 'UPLOADING')"
    )


def downgrade() -> None:
    # DOWNLOADING is a valid status before this revision too, so there is
    # nothing to restore.
    pass
