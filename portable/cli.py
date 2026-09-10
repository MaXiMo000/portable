"""portable check <export-path> <manifest.yaml> [--json]"""
from __future__ import annotations

import argparse
import contextlib
import json
import pathlib
import sys
import tempfile
import zipfile

from .check import FOUND, MISSING, UNVERIFIED, check_export
from .manifest import ManifestError, load_manifest

_TAG = {FOUND: "OK", MISSING: "--", UNVERIFIED: "??"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portable")
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser(
        "check", help="check a data export against a declared category manifest")
    check_p.add_argument("export_path", help="a JSON export file, or a directory export")
    check_p.add_argument("manifest", help="export-manifest.yaml")
    check_p.add_argument("--json", action="store_true", help="print the full report as JSON")

    args = parser.parse_args(argv)

    try:
        categories = load_manifest(args.manifest)
    except ManifestError as exc:
        sys.exit(f"portable: {exc}")

    export_path = pathlib.Path(args.export_path)
    if not export_path.exists():
        sys.exit(f"portable: no such export path: {export_path}")

    document = None
    export_dir = None
    with contextlib.ExitStack() as stack:
        if export_path.is_dir():
            export_dir = export_path
        elif zipfile.is_zipfile(export_path):
            # A Google-Takeout-style archive: extracted to a scratch
            # directory and then treated exactly like a directory export --
            # file_glob (and csv_column, above it) never need to know the
            # export arrived zipped rather than already unpacked.
            tmp = stack.enter_context(tempfile.TemporaryDirectory(prefix="portable-"))
            try:
                with zipfile.ZipFile(export_path) as zf:
                    zf.extractall(tmp)
            except zipfile.BadZipFile as exc:
                sys.exit(f"portable: could not read {export_path} as a zip archive: {exc}")
            export_dir = pathlib.Path(tmp)
        else:
            try:
                document = json.loads(export_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                sys.exit(f"portable: could not read {export_path} as JSON: {exc}")

        results = check_export(categories, document=document, export_dir=export_dir)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"[{_TAG[r['status']]}] {r['detail']}")
        n_missing = sum(1 for r in results if r["status"] == MISSING)
        n_unverified = sum(1 for r in results if r["status"] == UNVERIFIED)
        n_found = len(results) - n_missing - n_unverified
        summary = f"{n_found}/{len(results)} found"
        if n_missing:
            summary += f", {n_missing} missing"
        if n_unverified:
            summary += f", {n_unverified} unverified"
        print(f"\n{summary}")

    # unverified is "couldn't check," not "failed to deliver" -- only a
    # confirmed-missing category fails the exit code, same convention as
    # every sibling tool's pass/fail/unverified discipline.
    return 1 if any(r["status"] == MISSING for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
