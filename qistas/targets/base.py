from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BotReply:
    answer: str
    context: list[str] | None = None
    usage: dict = field(default_factory=dict)  # "transcript" always; "bot" if usage_path set
    latency_ms: float = 0.0
    error: str | None = None


def as_context(value) -> list[str] | None:
    """Accept a list of strings or of {"text": ...} documents."""
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    return [v["text"] if isinstance(v, dict) and "text" in v else str(v) for v in value]
