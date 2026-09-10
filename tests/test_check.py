"""Run: python tests/test_check.py"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from portable.check import FOUND, MISSING, UNVERIFIED, check_export


class TestJsonCategory(unittest.TestCase):
    def test_present_field_is_found(self):
        doc = {"user": {"email": "a@b.com"}}
        cats = [{"name": "profile", "json_path": "user.email"}]
        results = check_export(cats, document=doc)
        self.assertEqual(results[0]["status"], FOUND)

    def test_absent_field_is_missing(self):
        doc = {"user": {}}
        cats = [{"name": "profile", "json_path": "user.email"}]
        results = check_export(cats, document=doc)
        self.assertEqual(results[0]["status"], MISSING)

    def test_empty_string_field_is_missing_not_found(self):
        """A field that technically exists but holds nothing is exactly as
        absent as a field that doesn't exist -- the whole point is proving
        real data landed, not that a key was present."""
        doc = {"user": {"email": ""}}
        cats = [{"name": "profile", "json_path": "user.email"}]
        results = check_export(cats, document=doc)
        self.assertEqual(results[0]["status"], MISSING)

    def test_min_count_satisfied(self):
        doc = {"orders": [1, 2, 3]}
        cats = [{"name": "order_history", "json_path": "orders", "min_count": 2}]
        results = check_export(cats, document=doc)
        self.assertEqual(results[0]["status"], FOUND)

    def test_min_count_not_satisfied(self):
        doc = {"orders": [1]}
        cats = [{"name": "order_history", "json_path": "orders", "min_count": 2}]
        results = check_export(cats, document=doc)
        self.assertEqual(results[0]["status"], MISSING)
        self.assertIn("1 item(s)", results[0]["detail"])

    def test_min_count_against_a_non_list_value_is_missing(self):
        doc = {"orders": "not actually a list"}
        cats = [{"name": "order_history", "json_path": "orders", "min_count": 1}]
        results = check_export(cats, document=doc)
        self.assertEqual(results[0]["status"], MISSING)

    def test_json_category_against_a_directory_export_is_unverified(self):
        cats = [{"name": "profile", "json_path": "user.email"}]
        results = check_export(cats, export_dir=pathlib.Path("."))
        self.assertEqual(results[0]["status"], UNVERIFIED)
        self.assertIn("needs a JSON export file", results[0]["detail"])


class TestFileCategory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_matching_nonempty_file_is_found(self):
        (self.dir / "photos").mkdir()
        (self.dir / "photos" / "one.jpg").write_bytes(b"fake jpeg bytes")
        cats = [{"name": "photos", "file_glob": "photos/*.jpg"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], FOUND)

    def test_no_matching_file_is_missing(self):
        cats = [{"name": "photos", "file_glob": "photos/*.jpg"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], MISSING)

    def test_matching_but_empty_file_is_missing(self):
        (self.dir / "photos").mkdir()
        (self.dir / "photos" / "one.jpg").write_bytes(b"")
        cats = [{"name": "photos", "file_glob": "photos/*.jpg"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], MISSING)

    def test_file_category_against_a_json_document_is_unverified(self):
        cats = [{"name": "photos", "file_glob": "photos/*.jpg"}]
        results = check_export(cats, document={})
        self.assertEqual(results[0]["status"], UNVERIFIED)
        self.assertIn("needs a directory export", results[0]["detail"])


class TestCsvCategory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_csv(self, relpath: str, rows: list[str]):
        path = self.dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def test_column_with_non_empty_values_is_found(self):
        self._write_csv("Orders/orders.csv", ["order_id,item", "1001,Widget", "1002,Gadget"])
        cats = [{"name": "orders", "file_glob": "Orders/*.csv", "csv_column": "order_id"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], FOUND)

    def test_missing_column_name_is_missing(self):
        self._write_csv("Orders/orders.csv", ["order_id,item", "1001,Widget"])
        cats = [{"name": "orders", "file_glob": "Orders/*.csv", "csv_column": "nonexistent"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], MISSING)
        self.assertIn("not found", results[0]["detail"])

    def test_column_present_but_all_values_empty_is_missing(self):
        self._write_csv("Orders/orders.csv", ["order_id,item", ",Widget", ",Gadget"])
        cats = [{"name": "orders", "file_glob": "Orders/*.csv", "csv_column": "order_id"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], MISSING)

    def test_min_count_below_actual_non_empty_values_is_missing(self):
        self._write_csv("Orders/orders.csv", ["order_id,item", "1001,Widget"])
        cats = [{"name": "orders", "file_glob": "Orders/*.csv", "csv_column": "order_id", "min_count": 5}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], MISSING)

    def test_no_matching_csv_file_is_missing_same_as_file_glob(self):
        cats = [{"name": "orders", "file_glob": "Orders/*.csv", "csv_column": "order_id"}]
        results = check_export(cats, export_dir=self.dir)
        self.assertEqual(results[0]["status"], MISSING)
        self.assertIn("no non-empty file matching", results[0]["detail"])

    def test_csv_category_against_a_json_document_is_unverified(self):
        cats = [{"name": "orders", "file_glob": "Orders/*.csv", "csv_column": "order_id"}]
        results = check_export(cats, document={})
        self.assertEqual(results[0]["status"], UNVERIFIED)


class TestCheckExport(unittest.TestCase):
    def test_a_category_with_neither_kind_declared_is_unverified(self):
        results = check_export([{"name": "mystery"}], document={})
        self.assertEqual(results[0]["status"], UNVERIFIED)

    def test_mixed_categories_evaluated_independently(self):
        doc = {"user": {"email": "a@b.com"}, "orders": []}
        cats = [
            {"name": "profile", "json_path": "user.email"},
            {"name": "order_history", "json_path": "orders", "min_count": 1},
        ]
        results = check_export(cats, document=doc)
        statuses = {r["name"]: r["status"] for r in results}
        self.assertEqual(statuses, {"profile": FOUND, "order_history": MISSING})


if __name__ == "__main__":
    unittest.main()
