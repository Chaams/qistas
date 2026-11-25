from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import prompts


class JudgeError(RuntimeError):
    """The judge could not produce a valid score."""


@dataclass
class JudgeResult:
    score: float
    reason: str
    cost_usd: float | None
    input_tokens: int
    output_tokens: int


SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "number"}, "reason": {"type": "string"}},
    "required": ["score", "reason"],
    "additionalProperties": False,
}


@lru_cache
def _prices() -> dict:
    return tomllib.loads(Path(__file__).with_name("prices.toml").read_text(encoding="utf-8"))


def cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> float | None:
    p = _prices().get(provider, {}).get(model)
    if not p:
        return None
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def parse(text: str) -> tuple[float, str]:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
        score, reason = float(data["score"]), str(data["reason"])
    except (ValueError, KeyError, TypeError) as e:
        raise JudgeError(f"Judge returned invalid JSON: {text[:120]!r}") from e
    if not 0.0 <= score <= 1.0:
        raise JudgeError(f"Judge score out of range: {score}")
    return score, reason


class BaseJudge:
    provider = "base"

    def __init__(self, model: str):
        self.model = model

    def _complete(self, system: str, prompt: str) -> tuple[str, int, int]:
        raise NotImplementedError

    def score(self, task: str, payload: dict) -> JudgeResult:
        prompt = prompts.build(task, payload)
        tin = tout = 0
        last: JudgeError | None = None
        for _ in range(2):  # one retry on malformed output
            text, i, o = self._complete(prompts.SYSTEM, prompt)
            tin, tout = tin + i, tout + o
            try:
                score, reason = parse(text)
            except JudgeError as e:
                last = e
                continue
            return JudgeResult(score, reason, cost_usd(self.provider, self.model, tin, tout), tin, tout)
        assert last is not None
        raise last
