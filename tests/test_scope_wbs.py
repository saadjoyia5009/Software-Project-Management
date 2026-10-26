"""Database and validation tests for Part B scope control and WBS."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import database
from modules.scope_wbs_validation import (
    validate_change, validate_requirement, validate_wbs,
)
from modules.scope_wbs import _save_change_review


class ScopeWbsValidationTests(unittest.TestCase):
    def test_validation_rejects_incomplete_and_invalid_values(self):
        self.assertTrue(validate_requirement("", "", "Unknown", "Unknown"))
        self.assertTrue(validate_wbs("", "Unknown", 0, "Unknown"))
        self.assertTrue(validate_change("", "", -1, -1))


class ScopeWbsDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path, self.original_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_DIR = Path(self.directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "scope_test.db"
        database.initialize_db()
        self.project_id = database.fetch_one("SELECT project_id FROM projects LIMIT 1")["project_id"]

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.original_path, self.original_dir
        self.directory.cleanup()

    def test_requirement_crud_approval_and_scope_control(self):
        requirement_id = database.execute_query(
            "INSERT INTO requirements (project_id, title, description, priority) VALUES (?, ?, ?, ?)",
            (self.project_id, "Secure login", "Use authenticated access", "High"),
        )
        database.execute_query(
            "UPDATE requirements SET description=?, priority=?, status='Pending Approval' WHERE requirement_id=?",
            ("Use role-based authenticated access", "Critical", requirement_id),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            database.execute_query(
                "UPDATE requirements SET is_in_approved_scope=1 WHERE requirement_id=?",
                (requirement_id,),
            )
        database.execute_query(
            "UPDATE requirements SET status='Approved', is_in_approved_scope=1 WHERE requirement_id=?",
            (requirement_id,),
        )
        saved = database.fetch_one("SELECT status, is_in_approved_scope, priority FROM requirements WHERE requirement_id=?", (requirement_id,))
        self.assertEqual(saved, {"status": "Approved", "is_in_approved_scope": 1, "priority": "Critical"})

    def test_wbs_requires_approved_requirement_and_supports_hierarchy(self):
        unapproved_id = database.execute_query(
            "INSERT INTO requirements (project_id, title, description) VALUES (?, ?, ?)",
            (self.project_id, "Unapproved", "Must not reach WBS"),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            database.execute_query(
                "INSERT INTO wbs_tasks (project_id, requirement_id, task_name, duration_days) VALUES (?, ?, ?, ?)",
                (self.project_id, unapproved_id, "Blocked task", 1),
            )
        approved_id = database.execute_query(
            "INSERT INTO requirements (project_id, title, description, status, is_in_approved_scope) VALUES (?, ?, ?, 'Approved', 1)",
            (self.project_id, "Approved", "Allowed in scope"),
        )
        parent_id = database.execute_query(
            "INSERT INTO wbs_tasks (project_id, requirement_id, task_name, wbs_type, duration_days) VALUES (?, ?, ?, ?, ?)",
            (self.project_id, approved_id, "Patient portal", "Deliverable", 5),
        )
        child_id = database.execute_query(
            "INSERT INTO wbs_tasks (project_id, parent_task_id, requirement_id, task_name, wbs_type, duration_days) VALUES (?, ?, ?, ?, ?, ?)",
            (self.project_id, parent_id, approved_id, "Login package", "Work Package", 2),
        )
        child = database.fetch_one("SELECT parent_task_id, wbs_type FROM wbs_tasks WHERE task_id=?", (child_id,))
        self.assertEqual(child, {"parent_task_id": parent_id, "wbs_type": "Work Package"})
        with self.assertRaises(sqlite3.IntegrityError):
            database.execute_query("UPDATE requirements SET status='Rejected', is_in_approved_scope=0 WHERE requirement_id=?", (approved_id,))

    def test_wbs_parent_cycle_is_rejected_by_database(self):
        parent_id = database.execute_query(
            "INSERT INTO wbs_tasks (project_id, task_name, duration_days) VALUES (?, ?, ?)",
            (self.project_id, "Parent", 1),
        )
        child_id = database.execute_query(
            "INSERT INTO wbs_tasks (project_id, parent_task_id, task_name, duration_days) VALUES (?, ?, ?, ?)",
            (self.project_id, parent_id, "Child", 1),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            database.execute_query(
                "UPDATE wbs_tasks SET parent_task_id=? WHERE task_id=?",
                (child_id, parent_id),
            )

    def test_change_request_approval_updates_project_deadline_once(self):
        database.execute_query(
            "UPDATE projects SET deadline=? WHERE project_id=?",
            ("2026-10-01", self.project_id),
        )
        project_before = database.fetch_one(
            "SELECT approved_budget, revised_budget, scope, deadline FROM projects WHERE project_id=?",
            (self.project_id,),
        )
        change_id = database.execute_query(
            "INSERT INTO change_requests (project_id, title, justification, extra_cost, extra_duration_weeks, requested_by) VALUES (?, ?, ?, ?, ?, ?)",
            (self.project_id, "Add SMS", "Reminder support", 15000, 1, "Product owner"),
        )
        _save_change_review(
            change_id, self.project_id, "Add SMS", "Reminder support",
            "Product owner", 15000, 1, "Approved", "2026-10-24",
            "Fits release budget",
        )
        saved = database.fetch_one("SELECT status, decision_notes, extra_duration_weeks FROM change_requests WHERE change_id=?", (change_id,))
        self.assertEqual(saved, {"status": "Approved", "decision_notes": "Fits release budget", "extra_duration_weeks": 1})
        project_after = database.fetch_one(
            "SELECT approved_budget, revised_budget, scope, deadline FROM projects WHERE project_id=?",
            (self.project_id,),
        )
        self.assertEqual(project_after["deadline"], "2026-10-08")
        self.assertEqual(
            {key: value for key, value in project_after.items() if key != "deadline"},
            {key: value for key, value in project_before.items() if key != "deadline"},
        )
        _save_change_review(
            change_id, self.project_id, "Add SMS", "Reminder support",
            "Product owner", 15000, 1, "Approved", "2026-10-24",
            "Fits release budget",
        )
        self.assertEqual(
            database.fetch_one("SELECT deadline FROM projects WHERE project_id=?", (self.project_id,)),
            {"deadline": "2026-10-08"},
        )
        _save_change_review(
            change_id, self.project_id, "Add SMS", "Reminder support",
            "Product owner", 15000, 1, "Rejected", "2026-10-24",
            "Not approved",
        )
        self.assertEqual(
            database.fetch_one("SELECT deadline FROM projects WHERE project_id=?", (self.project_id,)),
            {"deadline": "2026-10-01"},
        )
