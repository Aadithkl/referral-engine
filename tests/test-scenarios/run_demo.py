"""run_demo.py -- Deterministic pipeline demonstration for all 6 personas.

Runs the Referral Engine's core math (scoring, tier mapping, curve building,
variable rewards, guardrails) against all 6 test persona JSON files.

NO API KEY REQUIRED -- purely deterministic computation.
Run from project root:  python tests/test-scenarios/run_demo.py
"""

import json
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

from referral_engine.core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from referral_engine.core.tier_mapper import classify_tier
from referral_engine.core.valley_surge import build_curve
from referral_engine.core.variable_reward import apply_to_curve
from referral_engine.core.penalty import compute_penalty
from referral_engine.config import settings

DATA_DIR = Path(__file__).resolve().parent / "data"
PERSONAS = [
    "power_user",
    "new_user",
    "builder_user",
    "amplifier_user",
    "declining_user",
    "sharer_user",
]

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
DIVIDER = "-" * 70


def load_persona(name: str) -> dict:
    path = DATA_DIR / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def extract_fields(profile: dict) -> dict:
    return {
        "twitter_followers": profile.get("twitter_followers", 0),
        "twitter_engagement": profile.get("twitter_engagement_rate", 0.0),
        "twitter_following": profile.get("twitter_following", 0),
        "account_age_days": profile.get("account_age_days", 0),
        "total_sessions_90d": profile.get("total_product_sessions_90d", 0),
        "feature_adoption": profile.get("feature_adoption_count", 0),
        "positive_outcomes": profile.get("positive_outcome_events", 0),
        "support_tickets": profile.get("support_tickets_90d", 0),
        "support_resolved": profile.get("support_tickets_resolved", 0),
        "activity_trend": profile.get("recent_activity_trend", "stable"),
        "prior_referrals": profile.get("prior_referrals_total", 0),
        "last_asked": profile.get("last_asked_at"),
        "last_declined": profile.get("last_declined_at"),
    }


def run_persona(name: str):
    data = load_persona(name)
    profile = data["data"]["profile"]
    p = extract_fields(profile)

    # Agent 2: Score Calculator
    reach, reach_reason = compute_reach(
        p["twitter_followers"], p["twitter_engagement"],
        p["twitter_following"], p["account_age_days"],
    )
    advocacy, adv_reason = compute_advocacy(
        p["total_sessions_90d"], p["feature_adoption"],
        p["positive_outcomes"], p["support_tickets"],
        p["support_resolved"], p["activity_trend"],
    )
    pcu, pcu_reason = compute_pcu(
        p["twitter_followers"], p["account_age_days"], advocacy,
    )

    # Tier classification
    tier, tier_reason = classify_tier(reach, advocacy)

    # Agent 3: Penalty calculator
    penalty, penalty_reasons = compute_penalty(
        p["account_age_days"], advocacy,
        p["support_tickets"], p["support_resolved"],
        p["last_asked"], p["last_declined"],
    )

    # Agent 4: Curve Designer (always runs)
    penalized_base = settings.BASE_REWARD * penalty
    milestones, total_budget = build_curve(tier, pcu, [1, pcu], 0.85, base_reward=penalized_base)
    enrich_curve = apply_to_curve(milestones, seed=42)

    # Print results
    tag = {
        "power_user": "Power User",
        "new_user": "New User",
        "builder_user": "Builder",
        "amplifier_user": "Amplifier",
        "declining_user": "Declining",
        "sharer_user": "Sharer",
    }.get(name, name)

    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  Persona: {tag}  ({name}){RESET}")
    print(f"{CYAN}{'='*70}{RESET}")

    print(f"\n  {BOLD}Input Profile{RESET}")
    print(f"    Followers: {p['twitter_followers']:,}  |  Engagement: {p['twitter_engagement']:.3f}  |  Following: {p['twitter_following']:,}")
    print(f"    Account Age: {p['account_age_days']}d  |  Sessions (90d): {p['total_sessions_90d']}")
    print(f"    Features: {p['feature_adoption']}  |  Support: {p['support_tickets']}/{p['support_resolved']} resolved")
    print(f"    Trend: {p['activity_trend']}  |  Prior Referrals: {p['prior_referrals']}")
    print(f"    Last Asked: {p['last_asked']}  |  Last Declined: {p['last_declined']}")

    print(f"\n  {BOLD}Agent 2: Score Calculator{RESET}")
    print(f"    {reach_reason}")
    print(f"    {adv_reason}")
    print(f"    {pcu_reason}")

    print(f"\n  {BOLD}Archetype Classification{RESET}")
    print(f"    {tier_reason}")

    print(f"\n  {BOLD}Agent 3: Penalty Calculator{RESET}")
    pen_pct = f"{penalty*100:.0f}%"
    pen_color = GREEN if penalty >= 0.8 else YELLOW if penalty >= 0.4 else RED
    print(f"    Penalty factor: {pen_color}{penalty:.4f} ({pen_pct}){RESET}")
    for reason in penalty_reasons:
        print(f"    {reason}")

    print(f"\n  {BOLD}Agent 4: Curve Designer{RESET}")
    print(f"    Total Budget: {total_budget:,.2f}")
    print(f"    Phases:")
    phases = {}
    for m in enrich_curve:
            phase = m["phase"]
            phases.setdefault(phase, []).append(m)
        for phase_name, milestones in phases.items():
            print(f"      {YELLOW}{phase_name.upper()}{RESET} ({len(milestones)} steps):")
            for m in milestones:
                rtype_color = ""
                if m["reward_type"] == "jackpot":
                    rtype_color = YELLOW
                elif m["reward_type"] == "mega_win":
                    rtype_color = GREEN
                print(f"        Step {m['step']:2d}: {m['baseline_reward']:8.2f} -> {m['variable_reward']:8.2f} ({rtype_color}{m['reward_type']}{RESET})")

    return {
        "persona": tag,
        "reach": reach,
        "advocacy": advocacy,
        "pcu": pcu,
        "tier": tier,
        "penalty": penalty,
    }


def main():
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  REFERRAL ENGINE -- Deterministic Pipeline Demo{RESET}")
    print(f"{BOLD}{CYAN}  Testing all 6 personas with mock data (no API key required){RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")

    results = {}
    for persona in PERSONAS:
        results[persona] = run_persona(persona)

    # ---- Summary table ----
    print(f"\n\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  SUMMARY -- All Personas{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")
    print(f"  {'Persona':<14} {'Reach':>6} {'Adv':>6} {'PCU':>5} {'Tier':<14} {'Penalty':>8}")
    print(f"  {'-'*14} {'-'*6} {'-'*6} {'-'*5} {'-'*14} {'-'*8}")
    for persona in PERSONAS:
        r = results[persona]
        pen_str = f"{r['penalty']*100:.0f}%"
        print(f"  {r['persona']:<14} {r['reach']:>6} {r['advocacy']:>6} {r['pcu']:>5} {r['tier']:<14} {pen_str:>8}")

    print(f"\n  {BOLD}Gate Thresholds (.env):{RESET}")
    print(f"    MIN_ADVOCACY_FOR_ASK={settings.MIN_ADVOCACY_FOR_ASK}  MIN_ACCOUNT_AGE={settings.MIN_ACCOUNT_AGE_DAYS}d")
    print(f"    DECLINED_COOLDOWN={settings.DECLINED_ASK_COOLDOWN_DAYS}d  FLOOR_GLOBAL={settings.PENALTY_FLOOR_GLOBAL}")
    print()


if __name__ == "__main__":
    main()
