"""Project configuration (`qistas.yaml`)."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Any, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HttpTarget(_Strict):
    kind: Literal["http"] = "http"
    url: str
    method: str = "POST"
    headers: dict[str, str] = {}
    # `{{turns}}` -> list of {"role","content"}; `{{last_user}}` -> last user message.
    body: dict[str, Any] = {"messages": "{{turns}}"}
    answer_path: str
    context_path: str | None = None
    usage_path: str | None = None
    timeout_s: float = 30
    health_url: str | None = None
    health_timeout_s: float = 120


class PythonTarget(_Strict):
    kind: Literal["python"] = "python"
    callable: str = Field(pattern=r"^[\w.]+:\w+$")


Target = Annotated[Union[HttpTarget, PythonTarget], Field(discriminator="kind")]


class JudgeConfig(_Strict):
    provider: Literal["anthropic", "gemini", "openai", "recorded"] = "anthropic"
    model: str | None = None
    cassette: str | None = None


class GateConfig(_Strict):
    thresholds: dict[str, float] = {}
    tag_thresholds: dict[str, dict[str, float]] = {}
    tolerance: float = 0.02
    latency_tolerance: float = 0.25
    max_failures: int = 0


class QistasConfig(_Strict):
    target: Target
    judge: JudgeConfig = JudgeConfig()
    gate: GateConfig = GateConfig()
    cases: list[str] = ["qistas/cases"]


_ENV = re.compile(r"\$\{(\w+)\}")


def _interpolate(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            name = m.group(1)
            if name not in os.environ:
                raise ValueError(f"Missing environment variable: {name}")
            return os.environ[name]
        return _ENV.sub(repl, value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


def load_config(path: Path | str) -> QistasConfig:
    """Read, interpolate `${VAR}` from the environment and validate a config file."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return QistasConfig.model_validate(_interpolate(raw))
    except ValidationError as e:
        raise ValueError(f"{path}: invalid configuration\n{e}") from e
