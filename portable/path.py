"""Resolve a small dot/bracket path into a parsed JSON document.

"orders[0].id" -> document["orders"][0]["id"]. Deliberately small: no
wildcards, no filters, no JSONPath dependency -- every real manifest entry
this tool exists for names one concrete field or list, not a query over
the whole document.
"""
from __future__ import annotations

import re

_SEGMENT = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


class PathError(Exception):
    pass


def resolve(document, path: str):
    """Returns the value at `path`. Raises PathError with a message naming
    exactly which segment failed, not just that the whole path did."""
    current = document
    walked = ""
    for m in _SEGMENT.finditer(path):
        key, index = m.groups()
        if key is not None:
            walked += ("." if walked else "") + key
            if not isinstance(current, dict):
                raise PathError(f"'{walked}': parent is not an object")
            if key not in current:
                raise PathError(f"'{walked}' does not exist")
            current = current[key]
        else:
            idx = int(index)
            walked += f"[{idx}]"
            if not isinstance(current, list):
                raise PathError(f"'{walked}': parent is not a list")
            if idx >= len(current):
                raise PathError(f"'{walked}': index out of range (list has {len(current)} item(s))")
            current = current[idx]
    return current
