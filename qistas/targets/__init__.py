"""Bot targets: how Qistas talks to the chatbot under test."""
from __future__ import annotations

from typing import Protocol

from ..cases import Turn
from ..config import HttpTarget, PythonTarget
from .base import BotReply


class Target(Protocol):
    def ask(self, turns: list[Turn]) -> BotReply: ...

    def wait_healthy(self) -> None: ...


def make_target(cfg: HttpTarget | PythonTarget) -> Target:
    if isinstance(cfg, HttpTarget):
        from .http import HttpBot

        return HttpBot(cfg)
    from .python import PythonBot

    return PythonBot(cfg)


__all__ = ["BotReply", "Target", "make_target"]
