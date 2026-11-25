from __future__ import annotations

from ..arabic import has_broken_text, script_ratio
from ..cases import Case
from ..targets import BotReply
from .base import MetricResult

MIN_ARABIC_RATIO = 0.6


def script_consistency(case: Case, reply: BotReply, judge) -> MetricResult:
    if has_broken_text(reply.answer):
        return MetricResult("script_consistency", 0.0, reason="texte cassé (caractères de remplacement ou formes isolées)")
    if case.expected_dialect:
        ratio = script_ratio(reply.answer)["arabic"]
        if ratio < MIN_ARABIC_RATIO:
            return MetricResult("script_consistency", 0.0, reason=f"seulement {ratio:.0%} de lettres arabes")
    return MetricResult("script_consistency", 1.0, reason="écriture cohérente")
