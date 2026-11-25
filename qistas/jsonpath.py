"""Minimal dotted-path lookup: `a.b[0].c`."""
from __future__ import annotations

import re
from typing import Any

_PART = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def get_path(obj: Any, path: str) -> Any:
    """Return the value at `path`; raise KeyError naming the path if any step is missing."""
    cur = obj
    for key, index in _PART.findall(path):
        try:
            cur = cur[int(index)] if index else cur[key]
        except (KeyError, IndexError, TypeError):
            raise KeyError(path) from None
    return cur
