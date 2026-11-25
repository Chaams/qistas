"""Arabic text normalization and script checks.

Normalization is applied before any lexical comparison so that spelling variants
(hamza forms, alef maqsura, ta marbuta, diacritics, tatweel) do not count as differences.
"""
from __future__ import annotations

import re
import unicodedata

# Harakat, tanwin, shadda, sukun, superscript alef, Quranic marks.
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_ALEF_VARIANTS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_PRESENTATION_FORMS = re.compile(r"[ﭐ-﷿ﹰ-﻿]")


def normalize(text: str) -> str:
    """Return `text` with Arabic orthographic variants unified (see module docstring)."""
    text = unicodedata.normalize("NFC", text)
    text = _DIACRITICS.sub("", text).replace(_TATWEEL, "")
    return text.translate(_ALEF_VARIANTS)


def tokens(text: str) -> list[str]:
    """Normalize, lowercase, then split on anything that is not a letter or digit."""
    return _TOKEN.findall(normalize(text).lower())


def _is_arabic(ch: str) -> bool:
    return "؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ" or "ࢠ" <= ch <= "ࣿ"


def script_ratio(text: str) -> dict[str, float]:
    """Share of letters (digits and punctuation ignored) that are Arabic, Latin or other."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return {"arabic": 0.0, "latin": 0.0, "other": 0.0}
    arabic = sum(_is_arabic(c) for c in letters)
    latin = sum(c.isascii() or "À" <= c <= "ɏ" for c in letters)
    n = len(letters)
    return {"arabic": arabic / n, "latin": latin / n, "other": (n - arabic - latin) / n}


def has_broken_text(text: str) -> bool:
    """True if the text holds replacement characters or isolated presentation forms."""
    return "�" in text or bool(_PRESENTATION_FORMS.search(text.replace("﻿", "")))
