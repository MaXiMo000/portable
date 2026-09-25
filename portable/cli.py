"""portable check <export-path> <manifest.yaml> [--json]

Deprecated: the check itself now lives in invariant (the `export_contains`
check type, invariant-verify >= 0.2.0). This command stays so existing
scripts keep working -- same arguments, same output, same exit codes.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings

from invariant.checks import export_contains

from .manifest import ManifestError, load_manifest

_TAG = {"found": "OK", "missing": "--", "unverified": "??"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="portable",
        epilog="Deprecated: use invariant's export_contains check (pip install invariant-verify).")
    sub = parser.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser(
        "check", help="check a data export against a declared category manifest")
    check_p.add_argument("export_path", help="a JSON export file, a directory export, or a .zip")
    check_p.add_argument("manifest", help="export-manifest.yaml")
    check_p.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args(argv)

    warnings.warn("portable is now invariant's export_contains check type; "
                  "see https://github.com/MaXiMo000/invariant", DeprecationWarning, stacklevel=2)

    try:
        categories = load_manifest(args.manifest)
    except ManifestError as exc:
        sys.exit(f"portable: {exc}")

    status, detail, evidence = export_contains.run(
        {"export": args.export_path, "categories": categories})
    results = evidence.get("categories")
    if results is None:
        # The export itself couldn't be read (missing path, bad zip, bad
        # JSON): a wrong argument, reported as one, not a per-category row.
        sys.exit(f"portable: {detail}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"[{_TAG[r['status']]}] {r['detail']}")
        n_missing = sum(1 for r in results if r["status"] == "missing")
        n_unverified = sum(1 for r in results if r["status"] == "unverified")
        summary = f"{len(results) - n_missing - n_unverified}/{len(results)} found"
        if n_missing:
            summary += f", {n_missing} missing"
        if n_unverified:
            summary += f", {n_unverified} unverified"
        print(f"\n{summary}")

    # Unchanged convention: only a confirmed-missing category fails.
    return 1 if any(r["status"] == "missing" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
