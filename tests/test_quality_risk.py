"""Part E tests for defects, quality checks, risk scoring, and PDPC actions."""

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

import database
from database import get_connection
from modules.quality_risk_service import (
    risk_priority, validate_defect, validate_pdpc, validate_project_member,
    validate_quality_check, validate_risk,
)


class QualityRiskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path, self.original_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_DIR = Path(self.directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "quality_risk_test.db"
        database.initialize_db()
        self.project_id = database.fetch_one("SELECT project_id FROM projects LIMIT 1")["project_id"]
        self.member_id = database.execute_query("INSERT INTO team_members (project_id, name, role) VALUES (?, ?, ?)", (self.project_id, "Noor", "QA Lead"))

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.original_path, self.original_dir
        self.directory.cleanup()

    def test_defect_crud_and_unresolved_critical_query(self):
        defect_id = database.execute_query("INSERT INTO defects (project_id, title, severity, assigned_member_id, status, reported_date) VALUES (?, ?, ?, ?, ?, ?)", (self.project_id, "Patient data exposed", "Critical", self.member_id, "Open", "2026-01-01"))
        critical = database.fetch_all("SELECT defect_id FROM defects WHERE project_id=? AND severity='Critical' AND status NOT IN ('Resolved', 'Verified', 'Closed')", (self.project_id,))
        self.assertEqual(critical, [{"defect_id": defect_id}])
        database.execute_query("UPDATE defects SET status='Resolved', resolution_notes=?, resolved_date=? WHERE defect_id=?", ("Access control fixed", "2026-01-02", defect_id))
        saved = database.fetch_one("SELECT status, resolution_notes, resolved_date FROM defects WHERE defect_id=?", (defect_id,))
        self.assertEqual(saved, {"status": "Resolved", "resolution_notes": "Access control fixed", "resolved_date": "2026-01-02"})
        database.execute_query("DELETE FROM defects WHERE defect_id=?", (defect_id,))
        self.assertIsNone(database.fetch_one("SELECT defect_id FROM defects WHERE defect_id=?", (defect_id,)))
        self.assertTrue(validate_defect("", "Bad", "Bad", "not a date"))

    def test_quality_check_persists_and_pending_failures_are_identified(self):
        database.execute_query("INSERT INTO quality_checks (project_id, item_name, inspection_date, result, tester_id) VALUES (?, ?, ?, ?, ?)", (self.project_id, "Validate booking", "2026-01-02", "Fail", self.member_id))
        database.execute_query("INSERT INTO quality_checks (project_id, item_name, inspection_date, result) VALUES (?, ?, ?, ?)", (self.project_id, "Check reports", "2026-01-02", "Not Tested"))
        attention = database.fetch_all("SELECT item_name FROM quality_checks WHERE project_id=? AND result IN ('Fail', 'Not Tested') ORDER BY item_name", (self.project_id,))
        self.assertEqual(attention, [{"item_name": "Check reports"}, {"item_name": "Validate booking"}])
        self.assertTrue(validate_quality_check("", "Bad", "bad date"))

    def test_risk_score_priority_ranking_and_score_safeguard(self):
        low_id = database.execute_query("INSERT INTO risks (project_id, title, likelihood, impact, risk_score, owner_id) VALUES (?, ?, ?, ?, ?, ?)", (self.project_id, "Low risk", 1, 2, 2, self.member_id))
        high_id = database.execute_query("INSERT INTO risks (project_id, title, likelihood, impact, risk_score, owner_id) VALUES (?, ?, ?, ?, ?, ?)", (self.project_id, "High risk", 5, 4, 20, self.member_id))
        ranked = database.fetch_all("SELECT risk_id, risk_score FROM risks WHERE project_id=? ORDER BY risk_score DESC", (self.project_id,))
        self.assertEqual(ranked, [{"risk_id": high_id, "risk_score": 20}, {"risk_id": low_id, "risk_score": 2}])
        self.assertEqual(risk_priority(20), "Critical")
        self.assertEqual(risk_priority(7), "Medium")
        with self.assertRaises(sqlite3.IntegrityError):
            database.execute_query("INSERT INTO risks (project_id, title, likelihood, impact, risk_score) VALUES (?, ?, ?, ?, ?)", (self.project_id, "Invalid", 2, 3, 10))
        self.assertTrue(validate_risk("", 0, 6, "Bad"))

    def test_pdpc_tracking_and_member_relationships(self):
        risk_id = database.execute_query("INSERT INTO risks (project_id, title, likelihood, impact, risk_score) VALUES (?, ?, ?, ?, ?)", (self.project_id, "Service outage", 4, 4, 16))
        action_id = database.execute_query("INSERT INTO pdpc_actions (risk_id, possible_problem, preventive_action, corrective_action, responsible_member_id, status) VALUES (?, ?, ?, ?, ?, ?)", (risk_id, "Server fails", "Monitor capacity", "Fail over", self.member_id, "Planned"))
        database.execute_query("UPDATE pdpc_actions SET status='Completed' WHERE action_id=?", (action_id,))
        saved = database.fetch_one("SELECT status, responsible_member_id FROM pdpc_actions WHERE action_id=?", (action_id,))
        self.assertEqual(saved, {"status": "Completed", "responsible_member_id": self.member_id})
        self.assertTrue(validate_pdpc("", "Bad"))
        with get_connection() as connection:
            validate_project_member(connection, self.project_id, self.member_id)
            with self.assertRaises(ValueError):
                validate_project_member(connection, self.project_id, 99999)
