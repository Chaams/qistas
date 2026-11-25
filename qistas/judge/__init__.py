"""LLM judge: one interface, several providers. Always uses the user's own API key."""
from __future__ import annotations

import os
from typing import Protocol

from ..config import JudgeConfig
from .base import JudgeError, JudgeResult

DEFAULT_MODEL = {"anthropic": "claude-sonnet-5-5"}


class Judge(Protocol):
    provider: str
    model: str

    def score(self, task: str, payload: dict) -> JudgeResult: ...


def make_judge(cfg: JudgeConfig) -> Judge:
    if cfg.provider == "recorded":
        from .recorded import RecordedJudge

        return RecordedJudge(cfg.cassette or "tests/cassettes")
    model = cfg.model or DEFAULT_MODEL.get(cfg.provider)
    if not model:
        raise JudgeError(f"judge.model is required for provider {cfg.provider}")
    if cfg.provider == "anthropic":
        from .anthropic import AnthropicJudge as cls
    elif cfg.provider == "openai":
        from .openai import OpenAIJudge as cls
    else:
        from .gemini import GeminiJudge as cls
    judge = cls(model)
    if os.environ.get("QISTAS_RECORD") == "1":
        from .recorded import RecordingJudge

        return RecordingJudge(judge, cfg.cassette or "tests/cassettes")
    return judge


__all__ = ["Judge", "JudgeError", "JudgeResult", "make_judge"]
