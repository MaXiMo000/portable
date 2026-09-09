"""Load and validate an export-manifest.yaml: the data categories a
privacy policy or export feature promises, and how to check each one is
actually present in a real export.
"""
from __future__ import annotations

import yaml


class ManifestError(ValueError):
    pass


def load_manifest(path: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: not valid YAML ({exc})") from exc
    except OSError as exc:
        raise ManifestError(f"{path}: {exc}") from exc

    if not isinstance(raw, dict) or "categories" not in raw:
        raise ManifestError(f"{path}: must be a mapping with a top-level 'categories' list")
    categories = raw["categories"]
    if not isinstance(categories, list) or not categories:
        raise ManifestError(f"{path}: 'categories' must be a non-empty list")

    seen = set()
    for i, cat in enumerate(categories):
        if not isinstance(cat, dict):
            raise ManifestError(f"{path}: categories[{i}] must be a mapping")
        name = cat.get("name")
        if not name or not isinstance(name, str):
            raise ManifestError(f"{path}: categories[{i}] is missing a string 'name'")
        if name in seen:
            raise ManifestError(f"{path}: duplicate category name '{name}'")
        seen.add(name)
        if "json_path" not in cat and "file_glob" not in cat:
            raise ManifestError(f"{path}: category '{name}' needs a 'json_path' or 'file_glob'")
        if "json_path" in cat and "file_glob" in cat:
            raise ManifestError(f"{path}: category '{name}' can't have both 'json_path' and 'file_glob'")

    return categories
