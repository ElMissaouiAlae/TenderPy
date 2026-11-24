"""Schema verification utilities for the persistence layer."""

from __future__ import annotations

from sqlalchemy import inspect

from persistence.database import Database
from persistence.exceptions import DatabaseConnectionError


def verify_schema(database: Database) -> bool:
    """Verify that the database schema matches expected structure.

    Performs a startup sanity check to ensure required tables and columns exist.
    This does not create or modify schema - that is handled by Alembic migrations.

    Args:
        database: Database instance to verify.

    Returns:
        True if schema verification passes.

    Raises:
        DatabaseConnectionError: if verification fails due to missing schema elements.
    """
    try:
        with database.session() as session:
            inspector = inspect(session.bind)

            # Check if tender_records table exists
            if "tender_records" not in inspector.get_table_names():
                raise DatabaseConnectionError(
                    "Required table 'tender_records' does not exist. "
                    "Run Alembic migrations to create the schema."
                )

            # Check for required columns
            required_columns = {
                "id",
                "tender_id",
                "organization_acronym",
                "procurement_type",
                "category",
                "publication_date",
                "reference_number",
                "tender_object",
                "public_buyer",
                "location",
                "deadline",
                "status",
                "created_at",
                "updated_at",
            }

            actual_columns = {col["name"] for col in inspector.get_columns("tender_records")}
            missing_columns = required_columns - actual_columns

            if missing_columns:
                raise DatabaseConnectionError(
                    f"Required columns missing from 'tender_records' table: {missing_columns}. "
                    "Run Alembic migrations to update the schema."
                )

            # Check for a unique constraint OR unique index on (tender_id, organization_acronym).
            # The model enforces this via a unique Index rather than a formal CONSTRAINT,
            # and Postgres ON CONFLICT (used by the repository's upserts) works against either.
            constraints = inspector.get_unique_constraints("tender_records")
            indexes = inspector.get_indexes("tender_records")

            unique_constraint_exists = any(
                set(constraint["column_names"]) == {"tender_id", "organization_acronym"}
                for constraint in constraints
            ) or any(
                index["unique"] and set(index["column_names"]) == {"tender_id", "organization_acronym"}
                for index in indexes
            )

            if not unique_constraint_exists:
                raise DatabaseConnectionError(
                    "Required unique constraint or unique index on (tender_id, organization_acronym) "
                    "does not exist. Run Alembic migrations to create the schema."
                )

            return True

    except DatabaseConnectionError:
        raise
    except Exception as exc:
        raise DatabaseConnectionError(f"Schema verification failed: {exc}") from exc
