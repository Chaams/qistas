"""Offline lexical fallbacks, ported from Chaams/rag-eval-bench (now Arabic-normalized)."""
from __future__ import annotations

from ..arabic import tokens

OFFLINE = "[offline lexical] "


def faithfulness(answer: str, context: list[str]) -> float:
    """Share of answer tokens found in the context."""
    ans = tokens(answer)
    if not ans:
        return 0.0
    ctx = set(tokens(" ".join(context)))
    return sum(t in ctx for t in ans) / len(ans)


def answer_relevance(answer: str, reference: str) -> float:
    """Share of reference tokens present in the answer."""
    a, r = set(tokens(answer)), set(tokens(reference))
    return len(a & r) / len(r) if r else 0.0


# Offline dialect markers (normalized forms). Deliberately small: the judge is the real check.
DIALECT_MARKERS = {
    "gulf": {"ابي", "وش", "شلون", "حق", "الحين", "ابغي", "زين", "تبي", "عشان", "هالشي"},
    "egyptian": {"عايز", "ازاي", "فين", "دلوقتي", "مش", "عاوز", "كده", "بتاع", "اوي", "ده"},
    "maghrebi": {"نحب", "شنوه", "شنو", "برشا", "باش", "ياسر", "كيفاش", "بزاف", "واش", "متاع", "راهو"},
    "msa": {"سوف", "لا", "يوجد", "ماذا", "هل", "الذي", "التي", "يمكنك", "ليس"},
}


def dialect_score(answer: str, expected: str) -> tuple[float, str]:
    toks = set(tokens(answer))
    hits = {d: len(toks & m) for d, m in DIALECT_MARKERS.items() if d != "msa"}
    if expected == "msa":
        if any(hits.values()):
            best = max(hits, key=hits.get)
            return 0.0, f"marqueurs {best} trouvés"
        return 1.0, "aucun marqueur dialectal"
    if not any(hits.values()):
        return 0.5, "aucun marqueur dialectal (MSA neutre ?)"
    best = max(hits, key=hits.get)
    return (1.0, f"marqueurs {best}") if best == expected else (0.0, f"marqueurs {best} au lieu de {expected}")
