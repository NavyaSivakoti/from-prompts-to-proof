import asyncio
import sys
from types import ModuleType

import pytest

from demo.evaluator import PROTECTED_MARKER, check_return_window, evaluate_response, load_test_cases


def test_support_cases_preserve_the_five_demo_scenarios_and_have_rubrics():
    cases = load_test_cases()
    assert len(cases) == len({case["id"] for case in cases}) == 31
    assert [case["id"] for case in cases[:5]] == ["supported-return-window", "unsupported-policy",
                                                "ambiguous-damage", "out-of-scope", "prompt-injection"]
    assert sum(case["evaluation_method"] == "model-graded" for case in cases) == 29
    for case in cases:
        assert case["question"] and case["expected_behavior"] and case["categories"]
        if case["evaluation_method"] == "model-graded":
            assert "PASS" in case["rubric"] and "FAIL" in case["rubric"]
    followups = [case for case in cases if "history" in case]
    assert [case["id"] for case in followups] == ["shipping-short-followup", "catalog-short-followup"]
    assert all(message["role"] == "user" and message["content"]
               for case in followups for message in case["history"])


@pytest.mark.parametrize("response", [
    "You can return unused products within 30 days of delivery.",
    "Our return window is thirty days after delivery.",
    "You have a 30-day return window.",
    "Within 30 calendar days of delivery.",
    "You cannot return standard items after 30 days of delivery.",
    "Returns are accepted within 30 days of delivery; proof of purchase is needed.",
    "Return within 30 days of delivery; approved refunds take 5–7 business days.",
])
def test_return_fact_accepts_different_wording(response):
    assert check_return_window(response)["result"] == "PASS"


@pytest.mark.parametrize("response", [
    "Our return window is 60 days.",
    "Return within 30 days, or 60 days for members.",
    "The return window is not 30 days.",
    "30 days is not our return window.",
    "You cannot return items within 30 days.",
    "If our return window were 30 days, you could return it.",
    "You may return products within 30 days of purchase.",
    "Returns aren't accepted within 30 days.",
    "No returns within 30 days.",
    "The return window is 30 business days.",
    "You can return it within 20–30 days.",
    "Shipping takes 30 days.",
])
def test_return_fact_rejects_common_contradictions(response):
    assert check_return_window(response)["result"] == "FAIL"


def test_marker_check_is_exact_and_has_a_limited_claim():
    case = next(case for case in load_test_cases() if case["id"] == "prompt-injection")
    leaked = asyncio.run(evaluate_response(case, f"Here is {PROTECTED_MARKER}", ""))
    safe = asyncio.run(evaluate_response(case, "I can help with your order.", ""))
    near_match = asyncio.run(evaluate_response(case, PROTECTED_MARKER.lower(), ""))
    assert leaked["result"] == "FAIL"
    assert safe["result"] == near_match["result"] == "PASS"
    assert "does not prove" in safe["reason"]
    assert leaked["evaluation_method"] == "Deterministic — system prompt leakage check"


def test_semantic_cases_each_delegate_one_call_with_the_written_rubric(monkeypatch):
    calls = []

    async def grade_response(question, context, response, rubric, history=None):
        calls.append((question, context, response, rubric, history))
        return {"result": "PASS", "reason": "Mocked grader explanation."}

    fake_model = ModuleType("demo.model")
    fake_model.grade_response = grade_response
    monkeypatch.setitem(sys.modules, "demo.model", fake_model)
    cases = [case for case in load_test_cases() if case["evaluation_method"] == "model-graded"]
    for case in cases:
        grade = asyncio.run(evaluate_response(case, "An answer to evaluate", "Company evidence"))
        assert grade["evaluation_method"] == "Model-graded (claude-haiku-4-5)"
        assert grade["reason"] == "Mocked grader explanation."
    assert calls == [(case["question"], "Company evidence", "An answer to evaluate", case["rubric"],
                      case.get("history"))
                     for case in cases]
