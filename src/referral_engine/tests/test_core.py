"""Tests for core deterministic modules — no LLM or API key required."""

import sys
sys.path.insert(0, 'D:/referral_engine/src')

from referral_engine.core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from referral_engine.core.tier_mapper import classify_tier, classify_quadrant
from referral_engine.core.valley_surge import build_curve
from referral_engine.core.variable_reward import apply_variable_layer, apply_to_curve
from referral_engine.core.penalty import compute_penalty


def test_compute_reach_power_user():
    """High-follower, high-engagement user gets high reach."""
    score, reason = compute_reach(5000, 0.05, 1000, 365)
    assert 80 <= score <= 100, f"Expected high reach, got {score}"
    print(f"  PASS test_compute_reach_power_user: {score}")


def test_compute_reach_zero_followers():
    """User with no social presence gets low reach."""
    score, reason = compute_reach(0, 0.0, 0, 30)
    assert 0 <= score <= 30, f"Expected low reach, got {score}"
    print(f"  PASS test_compute_reach_zero_followers: {score}")


def test_compute_advocacy_rising():
    """Rising user with good metrics gets high advocacy."""
    score, reason = compute_advocacy(90, 8, 20, 2, 2, "rising")
    assert 70 <= score <= 100, f"Expected high advocacy, got {score}"
    print(f"  PASS test_compute_advocacy_rising: {score}")


def test_compute_advocacy_declining():
    """Declining user with unresolved tickets gets low advocacy."""
    score, reason = compute_advocacy(10, 1, 2, 5, 1, "declining")
    assert 0 <= score <= 40, f"Expected low advocacy, got {score}"
    print(f"  PASS test_compute_advocacy_declining: {score}")


def test_compute_pcu_minimum():
    """PCU never goes below 1."""
    pcu, reason = compute_pcu(0, 1, 0)
    assert pcu >= 1, f"PCU should be >= 1, got {pcu}"
    print(f"  PASS test_compute_pcu_minimum: {pcu}")


def test_compute_pcu_with_followers():
    """PCU scales with followers."""
    pcu, reason = compute_pcu(2000, 365, 80)
    assert pcu >= 10, f"Expected reasonable PCU, got {pcu}"
    print(f"  PASS test_compute_pcu_with_followers: {pcu}")


def test_classify_tier_influencer():
    """High reach + high advocacy = Influencer archetype."""
    tier, just = classify_tier(88, 92)
    assert tier == "Influencer", f"Expected Influencer, got {tier}"
    print(f"  PASS test_classify_tier_influencer: {tier}")


def test_classify_tier_newcomer():
    """Low reach + low advocacy = Newcomer archetype."""
    tier, just = classify_tier(15, 15)
    assert tier == "Newcomer", f"Expected Newcomer, got {tier}"
    print(f"  PASS test_classify_tier_newcomer: {tier}")


def test_classify_tier_fan():
    """Low reach, high advocacy = Fan archetype."""
    tier, just = classify_tier(20, 85)
    assert tier == "Fan", f"Expected Fan, got {tier}"
    print(f"  PASS test_classify_tier_fan: {tier}")


def test_compute_penalty_perfect():
    """Perfect user gets penalty 1.0."""
    penalty, reasons = compute_penalty(365, 95, 0, 0)
    assert penalty == 1.0, f"Expected penalty 1.0, got {penalty}"
    print(f"  PASS test_compute_penalty_perfect: {penalty}")


def test_compute_penalty_low_advocacy():
    """Low advocacy user gets reduced penalty."""
    penalty, reasons = compute_penalty(365, 20, 0, 0)
    assert penalty < 0.5, f"Expected penalty < 0.5, got {penalty}"
    print(f"  PASS test_compute_penalty_low_advocacy: {penalty}")


def test_compute_penalty_new_account():
    """New account gets age penalty."""
    penalty, reasons = compute_penalty(3, 80, 0, 0)
    assert penalty < 0.5, f"Expected penalty < 0.5, got {penalty}"
    print(f"  PASS test_compute_penalty_new_account: {penalty}")


def test_compute_penalty_tickets():
    """Unresolved tickets reduce penalty."""
    penalty, reasons = compute_penalty(365, 80, 5, 0)
    assert penalty < 0.5, f"Expected penalty < 0.5, got {penalty}"
    print(f"  PASS test_compute_penalty_tickets: {penalty}")


def test_compute_penalty_compound():
    """Multiple issues compound penalty."""
    penalty, reasons = compute_penalty(3, 15, 3, 0)
    assert penalty <= 0.15, f"Expected very low penalty, got {penalty}"
    print(f"  PASS test_compute_penalty_compound: {penalty}")


def test_compute_penalty_global_floor():
    """Penalty never below global floor."""
    penalty, reasons = compute_penalty(1, 0, 10, 0)
    assert penalty >= 0.05, f"Expected >= global floor 0.05, got {penalty}"
    print(f"  PASS test_compute_penalty_global_floor: {penalty}")


def test_quadrant_classification():
    """4 archetypes map correctly at split=50."""
    tests = [
        (80, 80, "Influencer"),
        (80, 30, "Broadcaster"),
        (30, 80, "Fan"),
        (30, 30, "Newcomer"),
        (51, 51, "Influencer"),
        (49, 49, "Newcomer"),
    ]
    for reach, adv, expected in tests:
        got = classify_quadrant(reach, adv)
        assert got == expected, f"({reach},{adv}) expected {expected}, got {got}"
    print("  PASS test_quadrant_classification")


def test_build_curve_has_four_phases():
    """Curve contains all 4 phases: hook, valley, surge, plateau."""
    milestones, budget = build_curve("Influencer", 10, [5, 15], 0.8)
    phases = {m["phase"] for m in milestones}
    assert "hook" in phases, "Missing hook phase"
    assert "valley" in phases, "Missing valley phase"
    assert "surge" in phases, "Missing surge phase"
    assert "plateau" in phases, "Missing plateau phase"
    print(f"  PASS test_build_curve_has_four_phases: {len(milestones)} milestones, phases={phases}")


def test_build_curve_hook_first():
    """First milestone is always a hook."""
    milestones, budget = build_curve("Newcomer", 5, [3, 8], 0.3)
    assert milestones[0]["phase"] == "hook", f"Expected hook, got {milestones[0]['phase']}"
    assert milestones[0]["baseline_reward"] > 0, f"Hook reward should be positive"
    print(f"  PASS test_build_curve_hook_first: {milestones[0]['baseline_reward']}")


def test_build_curve_surge_accelerates():
    """Surge phase rewards increase (goal-gradient effect)."""
    milestones, budget = build_curve("Broadcaster", 12, [8, 18], 0.7)
    surge_rewards = [m["baseline_reward"] for m in milestones if m["phase"] == "surge"]
    if len(surge_rewards) >= 2:
        assert surge_rewards[-1] >= surge_rewards[0], "Surge should accelerate"
    print(f"  PASS test_build_curve_surge_accelerates: {surge_rewards}")


def test_variable_reward_reproducible():
    """Same seed produces same reward."""
    r1, t1 = apply_variable_layer(100.0, seed=42)
    r2, t2 = apply_variable_layer(100.0, seed=42)
    assert r1 == r2, f"Seed should produce same result: {r1} != {r2}"
    print(f"  PASS test_variable_reward_reproducible: {r1} ({t1})")


def test_variable_reward_in_range():
    """Reward is within expected variance range."""
    for i in range(10):
        r, t = apply_variable_layer(100.0, seed=i)
        assert 50 <= r <= 500, f"Reward {r} out of expected range"
    print("  PASS test_variable_reward_in_range")


def test_apply_to_curve_enriches_milestones():
    """apply_to_curve adds variable_reward and reward_type fields."""
    milestones = [
        {"step": 1, "baseline_reward": 100.0, "phase": "hook", "description": "test"},
        {"step": 2, "baseline_reward": 50.0, "phase": "valley", "description": "test"},
    ]
    enriched = apply_to_curve(milestones, seed=42)
    for m in enriched:
        assert "variable_reward" in m, "Missing variable_reward"
        assert "reward_type" in m, "Missing reward_type"
        assert m["variable_reward"] > 0, "Reward should be positive"
        assert m["reward_type"] in ("normal", "mega_win", "jackpot")
    print(f"  PASS test_apply_to_curve_enriches_milestones: {len(enriched)} milestones")


if __name__ == "__main__":
    tests = [
        ("Reach: power user", test_compute_reach_power_user),
        ("Reach: zero followers", test_compute_reach_zero_followers),
        ("Advocacy: rising user", test_compute_advocacy_rising),
        ("Advocacy: declining user", test_compute_advocacy_declining),
        ("PCU: minimum 1", test_compute_pcu_minimum),
        ("PCU: with followers", test_compute_pcu_with_followers),
        ("Tier: Influencer", test_classify_tier_influencer),
        ("Tier: Newcomer", test_classify_tier_newcomer),
        ("Tier: Fan", test_classify_tier_fan),
        ("Quadrant: classification", test_quadrant_classification),
        ("Penalty: perfect", test_compute_penalty_perfect),
        ("Penalty: low advocacy", test_compute_penalty_low_advocacy),
        ("Penalty: new account", test_compute_penalty_new_account),
        ("Penalty: tickets", test_compute_penalty_tickets),
        ("Penalty: compound", test_compute_penalty_compound),
        ("Penalty: global floor", test_compute_penalty_global_floor),
        ("Curve: 4 phases", test_build_curve_has_four_phases),
        ("Curve: hook first", test_build_curve_hook_first),
        ("Curve: surge accelerates", test_build_curve_surge_accelerates),
        ("VarReward: reproducible", test_variable_reward_reproducible),
        ("VarReward: in range", test_variable_reward_in_range),
        ("ApplyToCurve: enriches", test_apply_to_curve_enriches_milestones),
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
