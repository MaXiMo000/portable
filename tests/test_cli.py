"""Run: python tests/test_cli.py

Exercises the real CLI entry point end to end -- real temp files, real
argv, real stdout capture.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from portable.cli import main


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.manifest = self.dir / "export-manifest.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_export_all_categories_found(self):
        export = self.dir / "export.json"
        export.write_text(json.dumps({"user": {"email": "a@b.com"}, "orders": [1, 2]}))
        self.manifest.write_text(
            "categories:\n"
            "  - name: profile\n    json_path: user.email\n"
            "  - name: order_history\n    json_path: orders\n    min_count: 1\n"
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["check", str(export), str(self.manifest)])
        self.assertEqual(code, 0)
        self.assertIn("2/2 found", buf.getvalue())

    def test_json_export_missing_category_fails(self):
        export = self.dir / "export.json"
        export.write_text(json.dumps({"user": {}}))
        self.manifest.write_text("categories:\n  - name: profile\n    json_path: user.email\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["check", str(export), str(self.manifest)])
        self.assertEqual(code, 1)
        self.assertIn("[--]", buf.getvalue())
        self.assertIn("missing", buf.getvalue())

    def test_directory_export_file_glob(self):
        (self.dir / "export" / "photos").mkdir(parents=True)
        (self.dir / "export" / "photos" / "one.jpg").write_bytes(b"data")
        self.manifest.write_text("categories:\n  - name: photos\n    file_glob: photos/*.jpg\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["check", str(self.dir / "export"), str(self.manifest)])
        self.assertEqual(code, 0)
        self.assertIn("[OK]", buf.getvalue())

    def test_zip_export_is_treated_as_a_directory_export(self):
        """A Google-Takeout-style archive -- extracted to a scratch dir and
        checked exactly like an already-unpacked directory export."""
        import zipfile
        (self.dir / "photos").mkdir()
        (self.dir / "photos" / "one.jpg").write_bytes(b"data")
        zip_path = self.dir / "export.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(self.dir / "photos" / "one.jpg", "photos/one.jpg")
        self.manifest.write_text("categories:\n  - name: photos\n    file_glob: photos/*.jpg\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["check", str(zip_path), str(self.manifest)])
        self.assertEqual(code, 0)
        self.assertIn("[OK]", buf.getvalue())

    def test_zip_export_with_csv_column(self):
        import zipfile
        (self.dir / "Orders").mkdir()
        (self.dir / "Orders" / "orders.csv").write_text("order_id,item\n1001,Widget\n")
        zip_path = self.dir / "export.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(self.dir / "Orders" / "orders.csv", "Orders/orders.csv")
        self.manifest.write_text(
            "categories:\n  - name: orders\n    file_glob: Orders/*.csv\n    csv_column: order_id\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["check", str(zip_path), str(self.manifest)])
        self.assertEqual(code, 0)
        self.assertIn("[OK]", buf.getvalue())

    def test_a_bad_zip_file_is_a_clean_error_not_a_traceback(self):
        # A .zip-suffixed file that isn't actually a valid archive, and
        # isn't valid JSON either -- must fail cleanly either way it's read.
        bad = self.dir / "export.zip"
        bad.write_bytes(b"not a real zip or json")
        self.manifest.write_text("categories:\n  - name: x\n    json_path: a\n")
        with self.assertRaises(SystemExit) as ctx:
            main(["check", str(bad), str(self.manifest)])
        self.assertIn("portable:", str(ctx.exception))

    def test_wrong_export_kind_for_a_category_is_unverified_not_a_fail(self):
        (self.dir / "export").mkdir()
        self.manifest.write_text("categories:\n  - name: profile\n    json_path: user.email\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["check", str(self.dir / "export"), str(self.manifest)])
        self.assertEqual(code, 0)  # unverified never fails the exit code
        self.assertIn("[??]", buf.getvalue())

    def test_missing_export_path_is_a_clean_error_not_a_traceback(self):
        self.manifest.write_text("categories:\n  - name: x\n    json_path: a\n")
        with self.assertRaises(SystemExit) as ctx:
            main(["check", str(self.dir / "nope"), str(self.manifest)])
        self.assertIn("portable:", str(ctx.exception))

    def test_bad_manifest_is_a_clean_error_not_a_traceback(self):
        export = self.dir / "export.json"
        export.write_text("{}")
        self.manifest.write_text("not: a valid manifest\n")
        with self.assertRaises(SystemExit) as ctx:
            main(["check", str(export), str(self.manifest)])
        self.assertIn("portable:", str(ctx.exception))

    def test_non_json_export_file_is_a_clean_error(self):
        export = self.dir / "export.json"
        export.write_text("not valid json {{{")
        self.manifest.write_text("categories:\n  - name: x\n    json_path: a\n")
        with self.assertRaises(SystemExit) as ctx:
            main(["check", str(export), str(self.manifest)])
        self.assertIn("portable:", str(ctx.exception))

    def test_json_flag_prints_the_full_report(self):
        export = self.dir / "export.json"
        export.write_text(json.dumps({"user": {"email": "a@b.com"}}))
        self.manifest.write_text("categories:\n  - name: profile\n    json_path: user.email\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["check", str(export), str(self.manifest), "--json"])
        report = json.loads(buf.getvalue())
        self.assertEqual(report[0]["status"], "found")


if __name__ == "__main__":
    unittest.main()
