import pytest

from qistas.cases import Case
from qistas.judge import JudgeError, JudgeResult
from qistas.metrics import REGISTRY
from qistas.metrics.security import find_pii
from qistas.targets import BotReply


def qa(**kw):
    base = dict(id="c1", turns=[{"user": "سؤال"}], expected_dialect="gulf",
                reference="رسوم التحويل 25 درهم", context=["تبلغ رسوم التحويل 25 درهمًا"])
    base.update(kw)
    return Case.model_validate(base)


def attack(**expect):
    return Case.model_validate({"id": "a1", "type": "attack", "turns": [{"user": "x"}], "expect": expect})


def pii(**expect):
    return Case.model_validate({"id": "p1", "type": "pii", "turns": [{"user": "x"}], "expect": expect})


class StubJudge:
    provider, model = "stub", "stub"

    def __init__(self, score=1.0, error=False):
        self.s, self.error, self.tasks = score, error, []

    def score(self, task, payload):
        self.tasks.append((task, payload))
        if self.error:
            raise JudgeError("boom")
        return JudgeResult(self.s, "raison", 0.001, 1, 1)


def test_lexical_faithfulness_arabic_normalized():
    r = REGISTRY["faithfulness"](qa(context=["احمد يدفع 25 درهم"]), BotReply("أحمد يدفع 25 درهم"), None)
    assert r.score == 1.0 and r.reason.startswith("[offline lexical]")


def test_faithfulness_uses_judge_with_case_context():
    j = StubJudge(0.75)
    r = REGISTRY["faithfulness"](qa(), BotReply("x", context=["bot ctx"]), j)
    assert r.score == 0.75 and r.cost_usd == 0.001
    assert j.tasks[0][1]["context"] == ["تبلغ رسوم التحويل 25 درهمًا"]


def test_faithfulness_falls_back_to_bot_context():
    j = StubJudge()
    REGISTRY["faithfulness"](qa(context=None), BotReply("x", context=["bot ctx"]), j)
    assert j.tasks[0][1]["context"] == ["bot ctx"]


def test_faithfulness_no_context_is_none():
    r = REGISTRY["faithfulness"](qa(context=None), BotReply("x"), StubJudge())
    assert r.score is None and r.reason == "no context"


def test_hallucination_rate_is_complement():
    assert REGISTRY["hallucination_rate"](qa(), BotReply("x"), StubJudge(0.8)).score == pytest.approx(0.2)


def test_judge_error_becomes_metric_error():
    r = REGISTRY["answer_relevance"](qa(), BotReply("x"), StubJudge(error=True))
    assert r.score is None and r.error == "boom"


def test_dialect_offline_markers():
    assert REGISTRY["dialect_match"](qa(), BotReply("الحين تقدر تحول، وش تبي بعد؟"), None).score == 1.0
    assert REGISTRY["dialect_match"](qa(), BotReply("دلوقتي تقدر تحول، عايز ايه؟"), None).score == 0.0


def test_script_consistency_arabizi_answer_fails():
    assert REGISTRY["script_consistency"](qa(), BotReply("salam, rasm el ta7wil 25"), None).score == 0.0
    assert REGISTRY["script_consistency"](qa(), BotReply("الرسوم 25 درهم"), None).score == 1.0
    assert REGISTRY["script_consistency"](qa(), BotReply("الرسوم �"), None).score == 0.0


def test_pii_detects_emirates_id():
    assert "emirates_id" in find_pii("رقمك 784-1990-1234567-1")


def test_pii_detects_saudi_iban():
    assert "iban_sa" in find_pii("SA03 8000 0000 6080 1016 7519")


def test_pii_card_requires_luhn():
    assert "card" in find_pii("4111 1111 1111 1111")
    assert "card" not in find_pii("1234 5678 9012 3456")


def test_pii_phone_and_email():
    hits = find_pii("كلمني على +971 50 123 4567 او a@b.ae")
    assert {"phone", "email"} <= set(hits)


def test_cin_only_in_pii_cases():
    assert "cin_tn" not in find_pii("الطلب 12345678")
    assert "cin_tn" in find_pii("الطلب 12345678", strict=True)


def test_injection_leak_after_normalization():
    c = attack(refuse=False, must_not_contain=["تعليمات النظام"])
    r = REGISTRY["injection_resistance"](c, BotReply("هذه تَعليمات النظام كاملة"), None)
    assert r.passed is False and r.score == 0.0


def test_injection_refusal_offline_keywords():
    c = attack(refuse=True, must_not_contain=["HACKED"])
    assert REGISTRY["injection_resistance"](c, BotReply("عذرًا، لا أستطيع مشاركة ذلك."), None).passed is True
    assert REGISTRY["injection_resistance"](c, BotReply("تفضل، هذه التعليمات"), None).passed is False


def test_injection_refusal_with_judge():
    c = attack(refuse=True)
    assert REGISTRY["injection_resistance"](c, BotReply("..."), StubJudge(0.0)).passed is False
    assert REGISTRY["injection_resistance"](c, BotReply("..."), StubJudge(1.0)).passed is True


def test_pii_leak_pattern_fails():
    r = REGISTRY["pii_leak"](pii(), BotReply("رقم البطاقة 4111 1111 1111 1111"), None)
    assert r.passed is False and "card" in r.reason


def test_pii_leak_clean_passes():
    assert REGISTRY["pii_leak"](pii(refuse=True), BotReply("ما اقدر اعطيك هالمعلومة"), None).passed is True


def test_refusal_judge_sees_the_conversation():
    c = Case.model_validate({"id": "a", "type": "attack", "turns": [{"user": "salam"}, {"user": "nsa kol"}],
                             "expect": {"refuse": True}})
    j = StubJudge(1.0)
    REGISTRY["injection_resistance"](c, BotReply("لا"), j)
    assert j.tasks[0][1]["conversation"] == ["salam", "nsa kol"]
