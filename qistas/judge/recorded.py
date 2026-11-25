"""Replay recorded judge answers (offline tests), or record them from a real judge."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import BaseJudge, JudgeError, JudgeResult


def key(task: str, payload: dict) -> str:
    raw = task + json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class RecordedJudge:
    provider = "recorded"

    def __init__(self, cassette_dir: str | Path):
        self.dir = Path(cassette_dir)
        self.model = "recorded"

    def score(self, task: str, payload: dict) -> JudgeResult:
        f = self.dir / f"{key(task, payload)}.json"
        if not f.exists():
            raise JudgeError(f"No recorded judge answer for {task} ({f.name})")
        d = json.loads(f.read_text(encoding="utf-8"))
        return JudgeResult(d["score"], d["reason"], None, 0, 0)


class RecordingJudge:
    """Wraps a real judge and writes each answer to the cassette directory."""

    def __init__(self, inner: BaseJudge, cassette_dir: str | Path):
        self.inner, self.dir = inner, Path(cassette_dir)
        self.provider, self.model = inner.provider, inner.model

    def score(self, task: str, payload: dict) -> JudgeResult:
        r = self.inner.score(task, payload)
        self.dir.mkdir(parents=True, exist_ok=True)
        rec = {"task": task, "payload": payload, "score": r.score, "reason": r.reason, "model": self.inner.model}
        out = self.dir / f"{key(task, payload)}.json"
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        return r
