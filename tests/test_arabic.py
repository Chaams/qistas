from qistas.arabic import has_broken_text, normalize, script_ratio, tokens


def test_normalize_rules():
    assert normalize("أَحْمَد") == "احمد"
    assert normalize("إسلام آمن") == "اسلام امن"
    assert normalize("مستشفى") == "مستشفي"
    assert normalize("مدرسة") == "مدرسه"
    assert normalize("جمـــيل") == "جميل"


def test_tokens_normalized_and_split():
    assert tokens("مرحبًا، أحمد! 25 درهم") == ["مرحبا", "احمد", "25", "درهم"]


def test_script_ratio_arabizi():
    r = script_ratio("salam 3likom")
    assert r["latin"] > 0.9 and r["arabic"] == 0


def test_script_ratio_arabic():
    assert script_ratio("مرحبا بك")["arabic"] == 1.0


def test_script_ratio_empty():
    assert script_ratio("  ") == {"arabic": 0.0, "latin": 0.0, "other": 0.0}


def test_broken_text():
    assert has_broken_text("مرحبا �")
    assert has_broken_text("ﻻ")  # presentation-form ligature
    assert not has_broken_text("مرحبا بك")
