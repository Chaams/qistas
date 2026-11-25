from __future__ import annotations

import importlib
import inspect
import time

from ..cases import Turn
from ..config import PythonTarget
from .base import BotReply, as_context


class PythonBot:
    """Calls `module:func(question[, history])` -> {"answer", "context"?, "usage"?}."""

    def __init__(self, cfg: PythonTarget):
        self.cfg = cfg

    def wait_healthy(self) -> None:
        return None

    def _func(self):
        mod, name = self.cfg.callable.split(":")
        return getattr(importlib.import_module(mod), name)

    def ask(self, turns: list[Turn]) -> BotReply:
        history: list[dict] = []
        start = time.perf_counter()
        out: dict = {}
        try:
            func = self._func()
            takes_history = len(inspect.signature(func).parameters) >= 2
            for turn in turns:
                prior = list(history)
                history.append({"role": "user", "content": turn.user})
                out = func(turn.user, prior) if takes_history else func(turn.user)
                history.append({"role": "assistant", "content": str(out["answer"])})
        except Exception as e:  # the bot is user code: report, never crash the run
            return BotReply("", usage={"transcript": history}, latency_ms=_ms(start),
                            error=f"{type(e).__name__}: {e}")
        usage = {"transcript": history}
        if "usage" in out:
            usage["bot"] = out["usage"]
        return BotReply(str(out["answer"]), context=as_context(out.get("context")), usage=usage, latency_ms=_ms(start))


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
