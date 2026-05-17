"""Tests for guardrails and models — no LLM or API key required."""

import sys
sys.path.insert(0, 'D:/referral_engine/src')

from referral_engine.guardrails import (
    validate_no_pii, validate_score_range, validate_ask_decision, validate_curve_budget,
)
from referral_engine.models import (
    ScoreOutput, AskDecision, CurvePlan, AnalyzeRequest, AnalyzeResponse,
)
from referral_engine.state import ReferralState
from referral_engine.config import settings


class MockResult:
    def __init__(self, raw="", pydantic=None):
        self.raw = raw
        self.pydantic = pydantic


def test_validate_no_pii_clean():
    ok, msg = validate_no_pii(MockResult(raw="This is clean output about user behavior."))
    assert ok, f"Should pass: {msg}"
    print("  PASS test_validate_no_pii_clean")


def test_validate_no_pii_email_blocked():
    ok, msg = validate_no_pii(MockResult(raw="User john@example.com logged in."))
    assert not ok, "Should block email"
    print("  PASS test_validate_no_pii_email_blocked")


def test_validate_score_range_valid():
    scores = ScoreOutput(reach_score=68, advocacy_score=72, pcu=10, tier="Broadcaster", optimal_zone=[5, 15], reasoning="test")
    ok, msg = validate_score_range(MockResult(pydantic=scores))
    assert ok, f"Should pass: {msg}"
    print("  PASS test_validate_score_range_valid")


def test_validate_score_range_too_high():
    scores = ScoreOutput(reach_score=150, advocacy_score=72, pcu=10, tier="Broadcaster", optimal_zone=[5, 15], reasoning="test")
    ok, msg = validate_score_range(MockResult(pydantic=scores))
    assert not ok, "Should block out-of-range reach"
    print("  PASS test_validate_score_range_too_high")


def test_validate_ask_decision_valid():
    decision = AskDecision(should_ask=True, urgency=0.8, reasoning="test", gates_checked=[], gates_passed=[], gates_blocked=[], recommended_delay_hours=0)
    ok, msg = validate_ask_decision(MockResult(pydantic=decision))
    assert ok, f"Should pass: {msg}"
    print("  PASS test_validate_ask_decision_valid")


def test_validate_ask_decision_bad_urgency():
    decision = AskDecision(should_ask=True, urgency=1.5, reasoning="test", gates_checked=[], gates_passed=[], gates_blocked=[], recommended_delay_hours=0)
    ok, msg = validate_ask_decision(MockResult(pydantic=decision))
    assert not ok, "Should block urgency > 1.0"
    print("  PASS test_validate_ask_decision_bad_urgency")


def test_validate_curve_budget_valid():
    curve = CurvePlan(hook_reward=100, milestones=[{"step": 1}], total_reward=500, channel="email", tone="gentle_nudge", strategy_note="test")
    ok, msg = validate_curve_budget(MockResult(pydantic=curve))
    assert ok, f"Should pass: {msg}"
    print("  PASS test_validate_curve_budget_valid")


def test_validate_curve_budget_empty_milestones():
    curve = CurvePlan(hook_reward=100, milestones=[], total_reward=500, channel="email", tone="gentle_nudge", strategy_note="test")
    ok, msg = validate_curve_budget(MockResult(pydantic=curve))
    assert not ok, "Should block empty milestones"
    print("  PASS test_validate_curve_budget_empty_milestones")


def test_referral_state_defaults():
    state = ReferralState()
    assert state.status == "queued"
    assert state.reach_score == 0
    assert state.should_ask is True
    print("  PASS test_referral_state_defaults")


def test_analyze_request_model():
    req = AnalyzeRequest(user_id="user_123", data={"events": [], "profile": {}})
    assert req.user_id == "user_123"
    assert req.source == "product_backend"
    print("  PASS test_analyze_request_model")


def test_analyze_response_model():
    resp = AnalyzeResponse(job_id="job_abc", status="queued")
    assert resp.job_id == "job_abc"
    assert resp.estimated_time == "10-15s"
    print("  PASS test_analyze_response_model")


def test_settings_loads():
    assert settings.BASE_REWARD > 0
    assert settings.INFLUENCER_HOOK_RATIO > 0
    assert settings.INFLUENCER_PEAK_RATIO > 0
    assert settings.QUADRANT_REACH_SPLIT > 0
    assert settings.QUADRANT_ADVOCACY_SPLIT > 0
    print(f"  PASS test_settings_loads: BASE_REWARD={settings.BASE_REWARD}, INF_HOOK_RATIO={settings.INFLUENCER_HOOK_RATIO}, split={settings.QUADRANT_REACH_SPLIT}/{settings.QUADRANT_ADVOCACY_SPLIT}")


if __name__ == "__main__":
    tests = [
        ("Guard: PII clean", test_validate_no_pii_clean),
        ("Guard: PII email blocked", test_validate_no_pii_email_blocked),
        ("Guard: score range valid", test_validate_score_range_valid),
        ("Guard: score range too high", test_validate_score_range_too_high),
        ("Guard: ask decision valid", test_validate_ask_decision_valid),
        ("Guard: ask decision bad urgency", test_validate_ask_decision_bad_urgency),
        ("Guard: curve budget valid", test_validate_curve_budget_valid),
        ("Guard: curve budget empty", test_validate_curve_budget_empty_milestones),
        ("State: defaults", test_referral_state_defaults),
        ("Model: AnalyzeRequest", test_analyze_request_model),
        ("Model: AnalyzeResponse", test_analyze_response_model),
        ("Settings: loads correctly", test_settings_loads),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
