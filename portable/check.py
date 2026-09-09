"""Check each declared category in an export manifest against the actual
export: FOUND (real evidence exists) or MISSING (it doesn't). Two
statuses, not three -- there's no "contradicted" concept for a data
export the way `sourced` has for prose; a promised category is either
present or it isn't.
"""
from __future__ import annotations

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
            else:
                results.append(check_file_category(cat, export_dir))
        else:
            results.append({"name": name, "status": UNVERIFIED,
                             "detail": f"'{name}' has neither 'json_path' nor 'file_glob' declared"})
    return results
