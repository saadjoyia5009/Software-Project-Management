"""Part F tests for cross-module dashboard integration and reporting values."""

from datetime import date
import tempfile
import unittest
from pathlib import Path

import database
from modules.integration_dashboard import build_dashboard_snapshot


class IntegrationDashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path, self.original_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_DIR = Path(self.directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "integration_test.db"
        database.initialize_db()
        self.project_id = database.fetch_one("SELECT project_id FROM projects LIMIT 1")["project_id"]
        database.execute_query(
            "UPDATE projects SET approved_budget=?, revised_budget=?, duration_weeks=?, start_date=?, deadline=? WHERE project_id=?",
            (1000, 1000, 16, "2026-01-01", "2026-01-05", self.project_id),
        )

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.original_path, self.original_dir
        self.directory.cleanup()

    def test_snapshot_combines_delays_changes_costs_defects_quality_and_risks(self):
        task_id = database.execute_query(
            """INSERT INTO wbs_tasks
               (project_id, task_name, duration_days, planned_cost, progress,
                start_date, end_date, baseline_end_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.project_id, "Integration task", 2, 1200, 40,
             "2026-01-01", "2026-01-06", "2026-01-02", "Delayed"),
        )
        database.execute_query(
            "INSERT INTO cost_records (task_id, planned_cost, actual_cost, budgeted_value, record_date) VALUES (?, ?, ?, ?, ?)",
            (task_id, 1200, 700, 480, "2026-01-03"),
        )
        database.execute_query(
            "INSERT INTO change_requests (project_id, title, justification, extra_cost, status) VALUES (?, ?, ?, ?, ?)",
            (self.project_id, "Pending change", "Need review", 100, "Pending"),
        )
        database.execute_query(
            "INSERT INTO change_requests (project_id, title, justification, extra_cost, extra_duration_weeks, status) VALUES (?, ?, ?, ?, ?, ?)",
            (self.project_id, "Approved change", "Approved review", 50, 3, "Approved"),
        )
        database.execute_query(
            "INSERT INTO defects (project_id, title, severity, status, reported_date) VALUES (?, ?, ?, ?, ?)",
            (self.project_id, "Critical defect", "Critical", "Open", "2026-01-02"),
        )
        database.execute_query(
            "INSERT INTO quality_checks (project_id, item_name, result) VALUES (?, ?, ?)",
            (self.project_id, "Pending check", "Not Tested"),
        )
        database.execute_query(
            "INSERT INTO risks (project_id, title, likelihood, impact, risk_score, status) VALUES (?, ?, ?, ?, ?, ?)",
            (self.project_id, "Open risk", 4, 4, 16, "Open"),
        )
        project = database.fetch_one("SELECT * FROM projects WHERE project_id=?", (self.project_id,))
        tasks = database.fetch_all("SELECT * FROM wbs_tasks WHERE project_id=?", (self.project_id,))
        records = database.fetch_all("SELECT * FROM cost_records")
        changes = database.fetch_all("SELECT * FROM change_requests WHERE project_id=?", (self.project_id,))
        defects = database.fetch_all("SELECT * FROM defects WHERE project_id=?", (self.project_id,))
        checks = database.fetch_all("SELECT * FROM quality_checks WHERE project_id=?", (self.project_id,))
        risks = database.fetch_all("SELECT * FROM risks WHERE project_id=?", (self.project_id,))
        snapshot = build_dashboard_snapshot(project, tasks, records, changes, defects, checks, risks, date(2026, 1, 3))
        self.assertEqual(snapshot["progress"], 40)
        self.assertEqual(len(snapshot["delayed_tasks"]), 1)
        self.assertEqual(len(snapshot["pending_changes"]), 1)
        self.assertEqual(snapshot["approved_change_cost"], 50)
        self.assertEqual(snapshot["approved_budget"], 1000)
        self.assertEqual(snapshot["revised_approved_budget"], 1050)
        self.assertEqual(snapshot["baseline_duration_weeks"], 16)
        self.assertEqual(snapshot["revised_duration_weeks"], 19)
        self.assertEqual(len(snapshot["critical_defects"]), 1)
        self.assertEqual(len(snapshot["attention_checks"]), 1)
        self.assertEqual(len(snapshot["open_risks"]), 1)
        self.assertEqual(snapshot["evm"]["ac"], 700)
        self.assertAlmostEqual(snapshot["evm"]["cpi"], 480 / 700)
        self.assertTrue(any("Planned activity cost exceeds" in warning for warning in snapshot["warnings"]))
        self.assertTrue(any("Cost overrun" in warning for warning in snapshot["warnings"]))

    def test_snapshot_reports_no_exceptions_for_clean_data(self):
        project = database.fetch_one("SELECT * FROM projects WHERE project_id=?", (self.project_id,))
        snapshot = build_dashboard_snapshot(project, [], [], [], [], [], [], date(2026, 1, 1))
        self.assertEqual(snapshot["progress"], 0)
        self.assertEqual(snapshot["delayed_tasks"], [])
        self.assertEqual(snapshot["critical_defects"], [])
        self.assertEqual(snapshot["warnings"], [])

    def test_snapshot_does_not_double_count_an_already_stored_revised_budget(self):
        database.execute_query(
            "UPDATE projects SET revised_budget=? WHERE project_id=?",
            (1800, self.project_id),
        )
        database.execute_query(
            "INSERT INTO change_requests (project_id, title, justification, extra_cost, status) VALUES (?, ?, ?, ?, ?)",
            (self.project_id, "Approved change", "Approved review", 800, "Approved"),
        )
        project = database.fetch_one("SELECT * FROM projects WHERE project_id=?", (self.project_id,))
        changes = database.fetch_all("SELECT * FROM change_requests WHERE project_id=?", (self.project_id,))
        snapshot = build_dashboard_snapshot(project, [], [], changes, [], [], [], date(2026, 1, 1))
        self.assertEqual(snapshot["approved_budget"], 1000)
        self.assertEqual(snapshot["approved_change_cost"], 800)
        self.assertEqual(snapshot["revised_approved_budget"], 1800)

    def test_pending_change_does_not_change_budget_or_duration(self):
        database.execute_query(
            "INSERT INTO change_requests (project_id, title, justification, extra_cost, extra_duration_weeks, status) VALUES (?, ?, ?, ?, ?, ?)",
            (self.project_id, "Pending change", "Needs review", 800, 3, "Pending"),
        )
        project = database.fetch_one("SELECT * FROM projects WHERE project_id=?", (self.project_id,))
        changes = database.fetch_all("SELECT * FROM change_requests WHERE project_id=?", (self.project_id,))
        snapshot = build_dashboard_snapshot(project, [], [], changes, [], [], [], date(2026, 1, 1))
        self.assertEqual(snapshot["approved_budget"], 1000)
        self.assertEqual(snapshot["revised_approved_budget"], 1000)
        self.assertEqual(snapshot["baseline_duration_weeks"], 16)
        self.assertEqual(snapshot["revised_duration_weeks"], 16)
