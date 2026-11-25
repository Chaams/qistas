"""Test-case schema and loader."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CaseType = Literal["qa", "attack", "pii"]
Dialect = Literal["msa", "gulf", "egyptian", "maghrebi"]

DEFAULT_METRICS: dict[str, list[str]] = {
    "qa": ["faithfulness", "answer_relevance", "dialect_match", "script_consistency"],
    "attack": ["injection_resistance"],
    "pii": ["pii_leak"],
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Turn(_Strict):
    user: str


class Expect(_Strict):
    refuse: bool = False
    must_not_contain: list[str] = []


class Case(_Strict):
    id: str
    type: CaseType = "qa"
    turns: list[Turn] = Field(min_length=1)
    expected_dialect: Dialect | None = None
    reference: str | None = None
    context: list[str] | None = None
    metrics: list[str] | None = None
    expect: Expect | None = None
    tags: list[str] = []

    @model_validator(mode="after")
    def _attack_needs_expect(self) -> "Case":
        if self.type == "attack" and self.expect is None:
            raise ValueError("cases of type 'attack' require an 'expect' block")
        return self

    def effective_metrics(self) -> list[str]:
        return list(self.metrics) if self.metrics else list(DEFAULT_METRICS[self.type])


def _resolve(entry: str) -> Path:
    if entry.startswith("pack:"):
        from . import packs

        return packs.path(entry.removeprefix("pack:"))
    return Path(entry)


def _files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for entry in paths:
        p = _resolve(entry)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("*.yaml")) + sorted(p.rglob("*.yml")))
        else:
            raise ValueError(f"Cases path not found: {entry}")
    return out


def load_cases(paths: list[str]) -> list[Case]:
    """Load every `*.yaml` case file under `paths` (files, directories or `pack:<name>`)."""
    cases: list[Case] = []
    seen: dict[str, Path] = {}
    for f in _files(paths):
        items = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        if not isinstance(items, list):
            raise ValueError(f"{f}: expected a list of cases")
        for item in items:
            cid = item.get("id", "<no id>") if isinstance(item, dict) else "<not a mapping>"
            try:
                case = Case.model_validate(item)
            except ValidationError as e:
                raise ValueError(f"{f}: invalid case '{cid}'\n{e}") from e
            if case.id in seen:
                raise ValueError(f"Duplicate case id '{case.id}' in {seen[case.id]} and {f}")
            seen[case.id] = f
            cases.append(case)
    return cases
