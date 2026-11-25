from qistas import packs
from qistas.cases import load_cases


def test_base_pack_coverage():
    cases = load_cases([str(packs.path("base"))])
    assert len(cases) >= 60
    dialects = {c.expected_dialect for c in cases if c.type == "qa"}
    assert dialects >= {"msa", "gulf", "egyptian", "maghrebi"}
    assert sum(c.type == "attack" for c in cases) >= 16
    assert sum(c.type == "pii" for c in cases) >= 8


def test_load_cases_pack_prefix():
    assert len(load_cases(["pack:base"])) == len(load_cases([str(packs.path("base"))]))


def test_unknown_pack():
    import pytest

    with pytest.raises(ValueError, match="Unknown pack"):
        packs.path("nope")
