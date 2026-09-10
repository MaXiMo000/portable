"""Run: python tests/test_manifest.py"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from portable.manifest import ManifestError, load_manifest


class TestLoadManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "manifest.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text: str) -> str:
        self.path.write_text(text, encoding="utf-8")
        return str(self.path)

    def test_valid_manifest(self):
        p = self._write("categories:\n  - name: profile\n    json_path: user.email\n")
        cats = load_manifest(p)
        self.assertEqual(cats, [{"name": "profile", "json_path": "user.email"}])

    def test_missing_file_is_a_manifest_error_not_a_crash(self):
        with self.assertRaises(ManifestError):
            load_manifest(str(self.path))

    def test_not_yaml_is_a_manifest_error(self):
        p = self._write("not: valid: yaml: at: all:::")
        with self.assertRaises(ManifestError):
            load_manifest(p)

    def test_missing_categories_key_is_rejected(self):
        p = self._write("something_else: true\n")
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(p)
        self.assertIn("categories", str(ctx.exception))

    def test_empty_categories_list_is_rejected(self):
        p = self._write("categories: []\n")
        with self.assertRaises(ManifestError):
            load_manifest(p)

    def test_category_missing_name_is_rejected(self):
        p = self._write("categories:\n  - json_path: x\n")
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(p)
        self.assertIn("name", str(ctx.exception))

    def test_category_with_neither_kind_is_rejected(self):
        p = self._write("categories:\n  - name: x\n")
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(p)
        self.assertIn("json_path", str(ctx.exception))

    def test_category_with_both_kinds_is_rejected(self):
        p = self._write("categories:\n  - name: x\n    json_path: a\n    file_glob: b\n")
        with self.assertRaises(ManifestError):
            load_manifest(p)

    def test_csv_column_without_file_glob_is_rejected(self):
        p = self._write("categories:\n  - name: x\n    json_path: a\n    csv_column: b\n")
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(p)
        self.assertIn("csv_column", str(ctx.exception))

    def test_csv_column_with_file_glob_is_accepted(self):
        p = self._write("categories:\n  - name: x\n    file_glob: '*.csv'\n    csv_column: order_id\n")
        categories = load_manifest(p)
        self.assertEqual(categories[0]["csv_column"], "order_id")

    def test_duplicate_category_names_are_rejected(self):
        p = self._write(
            "categories:\n"
            "  - name: x\n    json_path: a\n"
            "  - name: x\n    json_path: b\n"
        )
        with self.assertRaises(ManifestError) as ctx:
            load_manifest(p)
        self.assertIn("duplicate", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
