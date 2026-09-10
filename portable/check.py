"""Check each declared category in an export manifest against the actual
export: FOUND (real evidence exists) or MISSING (it doesn't). Two
statuses, not three -- there's no "contradicted" concept for a data
export the way `sourced` has for prose; a promised category is either
present or it isn't.
"""
from __future__ import annotations

import csv
import pathlib

from .path import PathError, resolve

FOUND, MISSING, UNVERIFIED = "found", "missing", "unverified"

# What counts as "nothing here" for a presence check -- an empty container
# or an empty string is exactly as absent as the key not existing at all,
# and a category whose whole purpose is proving real data landed shouldn't
# read as satisfied by a field that technically exists but holds nothing.
_EMPTY = (None, "", [], {})


def check_json_category(category: dict, document) -> dict:
    name = category["name"]
    path = category["json_path"]
    try:
        value = resolve(document, path)
    except PathError as exc:
        return {"name": name, "status": MISSING,
                "detail": f"'{name}': {path} not found in the export ({exc})"}

    min_count = category.get("min_count")
    if min_count is not None:
        if not isinstance(value, list):
            return {"name": name, "status": MISSING,
                    "detail": f"'{name}': {path} exists but is not a list, so min_count can't apply"}
        if len(value) < min_count:
            return {"name": name, "status": MISSING,
                    "detail": (f"'{name}': {path} has {len(value)} item(s), "
                               f"expected at least {min_count}")}
        return {"name": name, "status": FOUND,
                "detail": f"'{name}': {path} has {len(value)} item(s)"}

    if value in _EMPTY:
        return {"name": name, "status": MISSING, "detail": f"'{name}': {path} exists but is empty"}
    return {"name": name, "status": FOUND, "detail": f"'{name}': {path} is present in the export"}


def check_file_category(category: dict, export_dir: pathlib.Path) -> dict:
    name = category["name"]
    pattern = category["file_glob"]
    matches = [p for p in export_dir.glob(pattern) if p.is_file() and p.stat().st_size > 0]
    if not matches:
        return {"name": name, "status": MISSING,
                "detail": f"'{name}': no non-empty file matching '{pattern}' found in the export"}
    return {"name": name, "status": FOUND,
            "detail": f"'{name}': {len(matches)} file(s) matching '{pattern}' found"}


def check_csv_category(category: dict, export_dir: pathlib.Path) -> dict:
    """Like check_file_category, but also opens the first matching file as
    CSV and requires a named column to have at least `min_count` (default
    1) non-empty values -- not just that a file matching the glob exists,
    which check_file_category alone can't tell apart from an empty export
    stub with the right filename and nothing real in it."""
    name = category["name"]
    pattern = category["file_glob"]
    column = category["csv_column"]
    min_count = category.get("min_count", 1)

    matches = sorted(p for p in export_dir.glob(pattern) if p.is_file() and p.stat().st_size > 0)
    if not matches:
        return {"name": name, "status": MISSING,
                "detail": f"'{name}': no non-empty file matching '{pattern}' found in the export"}

    csv_path = matches[0]
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if column not in (reader.fieldnames or []):
                return {"name": name, "status": MISSING,
                        "detail": f"'{name}': column '{column}' not found in {csv_path.name} "
                                  f"(columns: {', '.join(reader.fieldnames or []) or 'none'})"}
            non_empty = sum(1 for row in reader if (row.get(column) or "").strip())
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return {"name": name, "status": MISSING,
                "detail": f"'{name}': could not read {csv_path.name} as CSV ({exc})"}

    if non_empty < min_count:
        return {"name": name, "status": MISSING,
                "detail": f"'{name}': column '{column}' in {csv_path.name} has {non_empty} "
                          f"non-empty value(s), expected at least {min_count}"}
    return {"name": name, "status": FOUND,
            "detail": f"'{name}': column '{column}' in {csv_path.name} has {non_empty} non-empty value(s)"}


def check_export(categories: list[dict], *, document=None, export_dir: pathlib.Path | None = None) -> list[dict]:
    results = []
    for cat in categories:
        name = cat.get("name", "<unnamed>")
        if "json_path" in cat:
            if document is None:
                results.append({"name": name, "status": UNVERIFIED,
                                 "detail": f"'{name}' needs a JSON export file, but a directory was given"})
            else:
                results.append(check_json_category(cat, document))
        elif "file_glob" in cat:
            if export_dir is None:
                results.append({"name": name, "status": UNVERIFIED,
                                 "detail": f"'{name}' needs a directory export, but a JSON file was given"})
            elif "csv_column" in cat:
                results.append(check_csv_category(cat, export_dir))
            else:
                results.append(check_file_category(cat, export_dir))
        else:
            results.append({"name": name, "status": UNVERIFIED,
                             "detail": f"'{name}' has neither 'json_path' nor 'file_glob' declared"})
    return results
