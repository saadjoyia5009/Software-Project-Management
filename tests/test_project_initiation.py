"""Focused tests for Part A validation and additive database migrations."""

from datetime import date
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database
from database import _apply_part_a_migrations
from modules.project_initiation_validation import (
    validate_charter,
    validate_closure,
    validate_milestone,
    validate_stakeholder,
)


class ProjectInitiationValidationTests(unittest.TestCase):
    def test_valid_charter_has_no_errors(self):
        values = {
            "name": "Healthcare PM", "objective": "Deliver safely",
            "project_sponsor": "Sponsor", "project_manager": "Manager",
            "scope_in": "Portal", "scope_out": "Hardware",
            "start_date": date(2026, 1, 1), "deadline": date(2026, 2, 1),
            "approved_budget": 1000, "status": "Planning",
        }
        self.assertEqual(validate_charter(values), [])

    def test_invalid_charter_rejects_dates_budget_and_required_values(self):
        errors = validate_charter({"start_date": date(2026, 2, 1), "deadline": date(2026, 1, 1), "approved_budget": 0, "status": "Unknown"})
        self.assertTrue(any("Project name" in error for error in errors))
        self.assertTrue(any("Deadline" in error for error in errors))
        self.assertTrue(any("budget" in error.lower() for error in errors))

    def test_entity_validation(self):
        self.assertTrue(validate_stakeholder("", ""))
        self.assertTrue(validate_milestone("", date.today(), "Bad"))
        self.assertTrue(validate_closure(date.today(), "Planning", ""))


class ProjectInitiationMigrationTests(unittest.TestCase):
    def test_migration_adds_columns_without_removing_existing_data(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript("""
            CREATE TABLE projects (project_id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE milestones (milestone_id INTEGER PRIMARY KEY, project_id INTEGER, name TEXT);
            CREATE TABLE team_members (member_id INTEGER PRIMARY KEY, project_id INTEGER, name TEXT);
            INSERT INTO projects (project_id, name) VALUES (1, 'Existing project');
        """)
        _apply_part_a_migrations(connection)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
        self.assertIn("closure_summary", columns)
        self.assertIn("completed_date", {row["name"] for row in connection.execute("PRAGMA table_info(milestones)")})
        self.assertEqual(connection.execute("SELECT name FROM projects WHERE project_id=1").fetchone()["name"], "Existing project")
        connection.close()

    def test_reinitialization_preserves_part_a_records_and_enforces_foreign_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            original_path, original_dir = database.DATABASE_PATH, database.DATABASE_DIR
            try:
                database.DATABASE_DIR = Path(directory)
                database.DATABASE_PATH = database.DATABASE_DIR / "test.db"
                database.initialize_db()
                project = database.fetch_one("SELECT project_id FROM projects LIMIT 1")
                database.execute_query(
                    "INSERT INTO stakeholders (project_id, name, role) VALUES (?, ?, ?)",
                    (project["project_id"], "Clinical lead", "Approver"),
                )
                database.initialize_db()
                count = database.fetch_one("SELECT COUNT(*) AS total FROM stakeholders")
                self.assertEqual(count["total"], 1)
                with self.assertRaises(sqlite3.IntegrityError):
                    database.execute_query(
                        "INSERT INTO stakeholders (project_id, name, role) VALUES (?, ?, ?)",
                        (999999, "Invalid", "Invalid"),
                    )
            finally:
                database.DATABASE_PATH, database.DATABASE_DIR = original_path, original_dir
