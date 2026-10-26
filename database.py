
import sqlite3
from contextlib import contextmanager

from config import (
    DATABASE_DIR,
    DATABASE_PATH,
    SCHEMA_PATH,
    PROJECT_NAME,
    DEFAULT_BUDGET,
    DEFAULT_DURATION_WEEKS,
)


@contextmanager
def get_connection():
    """Create, manage, and close a SQLite database connection."""

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def initialize_db():
    """Create database tables, apply safe migrations, and seed a project."""

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Database schema not found: {SCHEMA_PATH}"
        )

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)
        _apply_part_a_migrations(connection)
        _apply_part_b_migrations(connection)
        _apply_part_c_migrations(connection)
        _apply_part_e_migrations(connection)

        existing_project = connection.execute(
            "SELECT project_id FROM projects LIMIT 1"
        ).fetchone()

        if existing_project is None:
            connection.execute(
                """
                INSERT INTO projects (
                    name,
                    objective,
                    scope,
                    duration_weeks,
                    approved_budget,
                    revised_budget,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    PROJECT_NAME,
                    (
                        "Manage healthcare operations and monitor "
                        "project scope, schedule, cost, quality, "
                        "risks and defects."
                    ),
                    (
                        "Appointments, laboratory reports, doctor "
                        "schedules, online consultations, billing "
                        "and project management modules."
                    ),
                    DEFAULT_DURATION_WEEKS,
                    DEFAULT_BUDGET,
                    DEFAULT_BUDGET,
                    "Planning",
                ),
            )


def _table_columns(connection, table_name):
    """Return the column names for a known SQLite table."""

    return {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


def _add_missing_columns(connection, table_name, columns):
    """Add nullable columns without changing or removing existing data."""

    existing_columns = _table_columns(connection, table_name)
    for column_name, column_definition in columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_definition}"
            )


def _apply_part_a_migrations(connection):
    """Apply additive Part A fields to databases created by earlier versions."""

    _add_missing_columns(
        connection,
        "projects",
        {
            "project_sponsor": "TEXT",
            "project_manager": "TEXT",
            "scope_in": "TEXT",
            "scope_out": "TEXT",
            "schedule_plan": "TEXT",
            "cost_plan": "TEXT",
            "quality_plan": "TEXT",
            "closure_date": "TEXT",
            "closure_final_status": "TEXT",
            "closure_summary": "TEXT",
            "outstanding_issues": "TEXT",
        },
    )
    _add_missing_columns(
        connection,
        "milestones",
        {"description": "TEXT", "completed_date": "TEXT"},
    )
    _add_missing_columns(
        connection,
        "team_members",
        {"responsibilities": "TEXT"},
    )


def _apply_part_b_migrations(connection):
    """Apply additive Scope Management and WBS fields to existing databases."""

    _add_missing_columns(
        connection,
        "wbs_tasks",
        {
            "wbs_type": (
                "TEXT NOT NULL DEFAULT 'Task' CHECK "
                "(wbs_type IN ('Deliverable', 'Task', 'Work Package'))"
            ),
        },
    )
    _add_missing_columns(
        connection,
        "change_requests",
        {"decision_notes": "TEXT"},
    )
    # Earlier project data used the Approved status before the separate
    # approved-scope flag was enforced. Keep those explicit approvals usable
    # by the WBS controls and the matching database safeguard.
    connection.execute(
        "UPDATE requirements SET is_in_approved_scope=1 "
        "WHERE status='Approved' AND is_in_approved_scope=0"
    )


def _apply_part_c_migrations(connection):
    """Apply additive Schedule and Resource Management fields."""

    _add_missing_columns(
        connection,
        "wbs_tasks",
        {
            "schedule_is_manual": "INTEGER NOT NULL DEFAULT 0 CHECK (schedule_is_manual IN (0, 1))",
            "baseline_start_date": "TEXT",
            "baseline_end_date": "TEXT",
        },
    )


def _apply_part_e_migrations(connection):
    """Apply additive Quality Management and Risk Control fields."""

    _add_missing_columns(connection, "defects", {"resolved_date": "TEXT"})


def execute_query(query, parameters=()):
    """Execute an INSERT, UPDATE, or DELETE query."""

    with get_connection() as connection:
        cursor = connection.execute(query, parameters)
        return cursor.lastrowid


def fetch_all(query, parameters=()):
    """Fetch and return all matching records as dictionaries."""

    with get_connection() as connection:
        rows = connection.execute(
            query, parameters
        ).fetchall()

        return [dict(row) for row in rows]


def fetch_one(query, parameters=()):
    """Fetch one matching record as a dictionary."""

    with get_connection() as connection:
        row = connection.execute(
            query, parameters
        ).fetchone()

        return dict(row) if row else None
