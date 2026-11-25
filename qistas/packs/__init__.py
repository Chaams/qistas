"""Test packs shipped with Qistas (use `pack:<name>` in `cases:`)."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parent


def names() -> list[str]:
    return sorted(p.name for p in _ROOT.iterdir() if p.is_dir() and not p.name.startswith("_"))


def path(name: str) -> Path:
    p = _ROOT / name
    if not p.is_dir() or name.startswith("_"):
        raise ValueError(f"Unknown pack: {name} (available: {', '.join(names())})")
    return p
