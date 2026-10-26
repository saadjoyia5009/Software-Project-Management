"""Part D tests for earned value calculations and cost-record persistence."""

from datetime import date
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database
from database import get_connection
from modules.evm_service import (
    calculate_evm, save_cost_record, update_cost_record, validate_cost_values,
)


class EvmFormulaTests(unittest.TestCase):
    def test_known_evm_values_and_warnings(self):
        tasks = [{"task_id": 1, "task_name": "Build", "planned_cost": 100, "progress": 40, "start_date": "2026-01-01", "end_date": "2026-01-10"}]
        records = [{"task_id": 1, "actual_cost": 60, "record_date": "2026-01-05"}]
        evm = calculate_evm(tasks, records, date(2026, 1, 5), 0.90)
        self.assertEqual(evm["pv"], 50)
        self.assertEqual(evm["ev"], 40)
        self.assertEqual(evm["ac"], 60)
        self.assertEqual(evm["cv"], -20)
        self.assertEqual(evm["sv"], -10)
        self.assertAlmostEqual(evm["cpi"], 40 / 60)
        self.assertAlmostEqual(evm["spi"], 0.8)
        self.assertEqual(len(evm["warnings"]), 4)

    def test_zero_denominators_are_safe(self):
        evm = calculate_evm([], [], date(2026, 1, 1))
        self.assertEqual(evm["pv"], 0)
        self.assertEqual(evm["ev"], 0)
        self.assertEqual(evm["ac"], 0)
        self.assertIsNone(evm["cpi"])
        self.assertIsNone(evm["spi"])
        self.assertTrue(validate_cost_values(0, 0, 0, date.today()))


class EvmPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_path, self.original_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_DIR = Path(self.directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "evm_test.db"
        database.initialize_db()
        self.project_id = database.fetch_one("SELECT project_id FROM projects LIMIT 1")["project_id"]
        self.task_id = database.execute_query("INSERT INTO wbs_tasks (project_id, task_name, duration_days, planned_cost, progress) VALUES (?, ?, ?, ?, ?)", (self.project_id, "Costed activity", 2, 1000, 50))

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.original_path, self.original_dir
        self.directory.cleanup()

    def test_cost_record_is_upserted_and_persists(self):
        with get_connection() as connection:
            record_id, created = save_cost_record(connection, self.project_id, self.task_id, 500, 400, date(2026, 1, 2))
        self.assertTrue(created)
        with get_connection() as connection:
            same_id, created = save_cost_record(connection, self.project_id, self.task_id, 600, 500, date(2026, 1, 2))
        self.assertFalse(created)
        self.assertEqual(record_id, same_id)
        records = database.fetch_all("SELECT actual_cost, budgeted_value, planned_cost FROM cost_records WHERE task_id=?", (self.task_id,))
        self.assertEqual(records, [{"actual_cost": 600.0, "budgeted_value": 500.0, "planned_cost": 1000.0}])

    def test_duplicate_direct_insert_and_unknown_activity_are_rejected(self):
        with get_connection() as connection:
            save_cost_record(connection, self.project_id, self.task_id, 1, 1, date(2026, 1, 2))
        with self.assertRaises(sqlite3.IntegrityError):
            database.execute_query("INSERT INTO cost_records (task_id, planned_cost, actual_cost, budgeted_value, record_date) VALUES (?, ?, ?, ?, ?)", (self.task_id, 1000, 2, 2, "2026-01-02"))
        with self.assertRaises(ValueError):
            with get_connection() as connection:
                save_cost_record(connection, self.project_id, 999999, 1, 1, date.today())

    def test_cost_record_can_be_corrected_by_its_unique_id(self):
        with get_connection() as connection:
            record_id, _ = save_cost_record(
                connection, self.project_id, self.task_id, 500, 400, date(2026, 1, 2),
            )
        with get_connection() as connection:
            update_cost_record(
                connection, self.project_id, record_id, 650, 550, date(2026, 1, 3),
            )
        saved = database.fetch_one(
            "SELECT cost_id, actual_cost, budgeted_value, record_date FROM cost_records WHERE cost_id=?",
            (record_id,),
        )
        self.assertEqual(saved, {
            "cost_id": record_id,
            "actual_cost": 650.0,
            "budgeted_value": 550.0,
            "record_date": "2026-01-03",
        })
        self.assertEqual(
            database.fetch_one("SELECT COUNT(*) AS total FROM cost_records")["total"], 1,
        )

    def test_cost_record_edit_rejects_another_record_date_for_same_activity(self):
        with get_connection() as connection:
            first_id, _ = save_cost_record(
                connection, self.project_id, self.task_id, 500, 400, date(2026, 1, 2),
            )
            save_cost_record(
                connection, self.project_id, self.task_id, 600, 500, date(2026, 1, 3),
            )
            with self.assertRaises(ValueError):
                update_cost_record(
                    connection, self.project_id, first_id, 700, 600, date(2026, 1, 3),
                )
