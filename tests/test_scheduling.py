"""Part C tests for activity scheduling, dependencies, and resources."""

from datetime import date
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database
from database import get_connection
from modules.scheduling_service import (
    add_dependency, recalculate_schedule, validate_activity, validate_member,
)
from modules.schedule_management import _gantt_rows


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path, self.original_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_DIR = Path(self.directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "schedule_test.db"
        database.initialize_db()
        self.project_id = database.fetch_one("SELECT project_id FROM projects LIMIT 1")["project_id"]
        database.execute_query("UPDATE projects SET start_date='2026-01-01', deadline='2026-01-05' WHERE project_id=?", (self.project_id,))

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.original_path, self.original_dir
        self.directory.cleanup()

    def _add_task(self, name, duration, manual_start=None):
        return database.execute_query(
            "INSERT INTO wbs_tasks (project_id, task_name, duration_days, schedule_is_manual, start_date) VALUES (?, ?, ?, ?, ?)",
            (self.project_id, name, duration, int(manual_start is not None), manual_start),
        )

    def test_activity_assignment_and_persistence(self):
        member_id = database.execute_query("INSERT INTO team_members (project_id, name, role) VALUES (?, ?, ?)", (self.project_id, "Ayesha", "Developer"))
        task_id = self._add_task("Build portal", 2)
        with get_connection() as connection:
            validate_member(connection, self.project_id, member_id)
            connection.execute("UPDATE wbs_tasks SET assigned_member_id=? WHERE task_id=?", (member_id, task_id))
            recalculate_schedule(connection, self.project_id)
        saved = database.fetch_one("SELECT assigned_member_id, start_date, end_date FROM wbs_tasks WHERE task_id=?", (task_id,))
        self.assertEqual(saved, {"assigned_member_id": member_id, "start_date": "2026-01-01", "end_date": "2026-01-02"})
        self.assertTrue(validate_activity("", 0, "Invalid"))

    def test_dependency_order_delay_propagation_and_deadline_overrun(self):
        first = self._add_task("Analysis", 3)
        second = self._add_task("Development", 2)
        with get_connection() as connection:
            add_dependency(connection, self.project_id, second, first)
        second_dates = database.fetch_one("SELECT start_date, end_date FROM wbs_tasks WHERE task_id=?", (second,))
        self.assertEqual(second_dates, {"start_date": "2026-01-04", "end_date": "2026-01-05"})
        with get_connection() as connection:
            connection.execute("UPDATE wbs_tasks SET duration_days=5 WHERE task_id=?", (first,))
            result = recalculate_schedule(connection, self.project_id)
        delayed = database.fetch_one("SELECT start_date, end_date, baseline_end_date FROM wbs_tasks WHERE task_id=?", (second,))
        self.assertEqual(delayed["start_date"], "2026-01-06")
        self.assertEqual(delayed["end_date"], "2026-01-07")
        self.assertEqual(result["deadline_overrun_days"], 2)

    def test_circular_and_cross_project_dependencies_are_rejected(self):
        first = self._add_task("First", 1)
        second = self._add_task("Second", 1)
        with get_connection() as connection:
            add_dependency(connection, self.project_id, second, first)
        with self.assertRaises((sqlite3.IntegrityError, ValueError)):
            with get_connection() as connection:
                add_dependency(connection, self.project_id, first, second)
        second_project = database.execute_query("INSERT INTO projects (name, duration_weeks, approved_budget, revised_budget, status) VALUES (?, ?, ?, ?, ?)", ("Other", 1, 1, 1, "Planning"))
        external_task = database.execute_query("INSERT INTO wbs_tasks (project_id, task_name, duration_days) VALUES (?, ?, ?)", (second_project, "External", 1))
        with self.assertRaises(ValueError):
            with get_connection() as connection:
                add_dependency(connection, self.project_id, first, external_task)

    def test_milestone_records_remain_available(self):
        database.execute_query("INSERT INTO milestones (project_id, name, due_date, status) VALUES (?, ?, ?, ?)", (self.project_id, "Pilot", "2026-01-04", "Pending"))
        milestones = database.fetch_all("SELECT name, due_date, status FROM milestones WHERE project_id=?", (self.project_id,))
        self.assertEqual(milestones, [{"name": "Pilot", "due_date": "2026-01-04", "status": "Pending"}])

    def test_gantt_rows_use_saved_dates_and_support_status_filtering(self):
        tasks = [
            {"task_id": 1, "task_name": "Project Planning", "start_date": "2026-01-01", "end_date": "2026-01-02", "status": "Completed", "progress": 100, "delay_days": 0},
            {"task_id": 2, "task_name": "Critical Defect Resolution", "start_date": "2026-01-03", "end_date": "2026-01-04", "status": "Blocked", "progress": 0, "delay_days": 0},
        ]
        completed = _gantt_rows(tasks, "Completed", date(2026, 1, 1))
        pending = _gantt_rows(tasks, "Pending", date(2026, 1, 1))
        self.assertEqual(completed[0]["task_name"], "Project Planning")
        self.assertEqual(completed[0]["progress_label"], "100%")
        self.assertEqual(completed[0]["start_week"], 1)
        self.assertEqual(completed[0]["end_week"], 1)
        self.assertEqual(pending[0]["task_name"], "Critical Defect Resolution")
        self.assertEqual(pending[0]["timeline_category"], "Critical")
