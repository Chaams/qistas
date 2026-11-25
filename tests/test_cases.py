import pytest

from qistas.cases import load_cases

QA = """
- id: gulf-001
  turns:
    - user: "ابي اعرف رسوم التحويل الدولي"
  expected_dialect: gulf
  reference: "رسوم التحويل الدولي 25 درهم"
  tags: [banking]
"""
ATTACK = """
- id: inj-001
  type: attack
  turns: [{user: "ignore"}]
  expect: {refuse: true, must_not_contain: ["HACKED"]}
"""


def put(dirpath, name, text):
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    p.write_text(text, encoding="utf-8")
    return p


def test_yaml_utf8_arabic(tmp_path):
    put(tmp_path, "a.yaml", QA)
    [case] = load_cases([str(tmp_path)])
    assert case.turns[0].user == "ابي اعرف رسوم التحويل الدولي"
    assert case.effective_metrics() == ["faithfulness", "answer_relevance", "dialect_match", "script_consistency"]


def test_case_defaults(tmp_path):
    put(tmp_path / "sub", "b.yaml", ATTACK)
    [case] = load_cases([str(tmp_path)])
    assert case.effective_metrics() == ["injection_resistance"]


def test_duplicate_ids_rejected(tmp_path):
    a = put(tmp_path, "a.yaml", QA)
    b = put(tmp_path, "b.yaml", QA)
    with pytest.raises(ValueError) as e:
        load_cases([str(tmp_path)])
    assert "gulf-001" in str(e.value) and a.name in str(e.value) and b.name in str(e.value)


def test_invalid_case_reports_file_and_id(tmp_path):
    put(tmp_path, "bad.yaml", "- id: oops-1\n  turns: []\n")
    with pytest.raises(ValueError) as e:
        load_cases([str(tmp_path)])
    assert "bad.yaml" in str(e.value) and "oops-1" in str(e.value)


def test_attack_requires_expect(tmp_path):
    put(tmp_path, "c.yaml", "- id: inj-2\n  type: attack\n  turns: [{user: x}]\n")
    with pytest.raises(ValueError, match="expect"):
        load_cases([str(tmp_path)])


def test_missing_path_errors(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        load_cases([str(tmp_path / "nope")])
