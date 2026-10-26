"""Tests for the shared team resource register used across project modules."""

import tempfile
import unittest
from pathlib import Path

import database
from modules.team_resources import validate_team_member


class TeamResourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path, self.original_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_DIR = Path(self.directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "team_test.db"
        database.initialize_db()
        self.project_id = database.fetch_one("SELECT project_id FROM projects LIMIT 1")["project_id"]

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.original_path, self.original_dir
        self.directory.cleanup()

    def test_team_member_persists_and_deletion_clears_activity_assignment(self):
        member_id = database.execute_query(
            """INSERT INTO team_members
               (project_id, name, role, email, responsibilities)
               VALUES (?, ?, ?, ?, ?)""",
            (self.project_id, "Ayesha", "Developer", "ayesha@example.test", "Build portal"),
        )
        task_id = database.execute_query(
            """INSERT INTO wbs_tasks
               (project_id, task_name, duration_days, assigned_member_id)
               VALUES (?, ?, ?, ?)""",
            (self.project_id, "Portal", 1, member_id),
        )
        member = database.fetch_one("SELECT role, responsibilities FROM team_members WHERE member_id=?", (member_id,))
        self.assertEqual(member, {"role": "Developer", "responsibilities": "Build portal"})
        database.execute_query("DELETE FROM team_members WHERE member_id=?", (member_id,))
        task = database.fetch_one("SELECT assigned_member_id FROM wbs_tasks WHERE task_id=?", (task_id,))
        self.assertIsNone(task["assigned_member_id"])

    def test_member_validation_rejects_missing_name_or_role(self):
        self.assertTrue(validate_team_member("", "Developer"))
        self.assertTrue(validate_team_member("Ayesha", ""))
        self.assertEqual(validate_team_member("Ayesha", "Developer"), [])
