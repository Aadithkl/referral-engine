"""test_20_users.py — Run 20 test personas through the full pipeline and persist curves.

Uses deterministic core math (no LLM). All curves saved to SQLite.
Run from project root: python tests/test_20_users.py
"""

import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

from referral_engine.core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from referral_engine.core.tier_mapper import classify_tier
from referral_engine.core.valley_surge import build_curve
from referral_engine.core.variable_reward import apply_to_curve
from referral_engine.core.penalty import compute_penalty
from referral_engine.config import settings
from referral_engine import storage

DATA_FILE = PROJECT_ROOT / "data" / "test_users_20.json"

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def load_users() -> list[dict]:
    with open(DATA_FILE) as f:
        return json.load(f)


def run_user(user: dict) -> dict:
    p = user["profile"]
    f = p.get("twitter_followers", 0)
    eng = p.get("twitter_engagement_rate", 0.0)
    fng = p.get("twitter_following", 0)
    age = p.get("account_age_days", 0)
    ses = p.get("total_product_sessions_90d", 0)
    feat = p.get("feature_adoption_count", 0)
    out = p.get("positive_outcome_events", 0)
    tix = p.get("support_tickets_90d", 0)
    res = p.get("support_tickets_resolved", 0)
    trend = p.get("recent_activity_trend", "stable")

    reach, _ = compute_reach(f, eng, fng, age)
    adv, _ = compute_advocacy(ses, feat, out, tix, res, trend)
    pcu, _ = compute_pcu(f, age, adv)
    archetype, _ = classify_tier(reach, adv)

    penalty, reasons = compute_penalty(age, adv, tix, res)
    urgency = min(1.0, adv / 100.0)

    penalized_base = settings.BASE_REWARD * penalty
    milestones, total_budget = build_curve(archetype, pcu, [1, pcu], max(urgency, 0.5), base_reward=penalized_base)
    enriched = apply_to_curve(milestones, seed=42)
    channel = "push" if urgency > 0.7 else "in-app" if urgency > 0.3 else "email"
    tone = "urgent" if urgency > 0.8 else "opportunity" if urgency > 0.5 else "gentle_nudge"

    return {
        "user_id": user["user_id"],
        "label": user["label"],
        "archetype": archetype,
        "reach_score": reach,
        "advocacy_score": adv,
        "pcu": pcu,
        "base_reward": settings.BASE_REWARD,
        "total_budget": total_budget,
        "step_count": len(milestones),
        "milestones": enriched,
        "urgency": urgency,
        "penalty_factor": penalty,
        "penalty_reasons": reasons,
        "should_ask": True,
        "blocks": [],
        "status": "completed",
        "channel": channel,
        "tone": tone,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def save_all(results: list[dict]):
    for r in results:
        await storage.save_curve(r["user_id"], r)


def print_summary(results: list[dict]):
    print(f"\n{BOLD}{CYAN}{'='*90}{RESET}")
    print(f"{BOLD}{CYAN}  20-USER CURVE GENERATION - Summary{RESET}")
    print(f"{CYAN}{'='*90}{RESET}")
    print(f"{'User':<24} {'Archetype':<14} {'Reach':>6} {'Adv':>6} {'PCU':>5} {'Penalty':>8} {'Budget':>10} {'Steps':>6} {'Reasons'}")
    print(f"{'-'*24} {'-'*14} {'-'*6} {'-'*6} {'-'*5} {'-'*8} {'-'*10} {'-'*6} {'-'*30}")

    counts = {"Influencer": 0, "Broadcaster": 0, "Fan": 0, "Newcomer": 0}
    total_budget_all = 0.0

    for r in results:
        counts[r["archetype"]] = counts.get(r["archetype"], 0) + 1
        total_budget_all += r["total_budget"]
        pen = f"{r['penalty_factor']*100:.0f}%"
        reasons = r["penalty_reasons"][0] if len(r["penalty_reasons"]) == 1 and r["penalty_factor"] >= 0.99 else r["penalty_reasons"][0][:40] + "..." if r["penalty_reasons"] else ""
        print(f"  {r['label']:<22} {r['archetype']:<14} {r['reach_score']:>6} {r['advocacy_score']:>6} {r['pcu']:>5} {pen:>8} {r['total_budget']:>10.2f} {r['step_count']:>6}   {reasons}")

    print(f"\n{BOLD}Archetype Distribution:{RESET}")
    for a in ["Influencer", "Broadcaster", "Fan", "Newcomer"]:
        print(f"  {a:<14} {counts.get(a, 0)} users")
    print(f"\n{BOLD}Total curves:{RESET} {len(results)} (all generated, no blocking)")
    print(f"{BOLD}Total Budget:{RESET} {total_budget_all:,.2f}")
    print()


async def main():
    users = load_users()
    print(f"\n{BOLD}{CYAN}{'='*90}{RESET}")
    print(f"{BOLD}{CYAN}  REFERRAL ENGINE - 20-User Test Run (no API key){RESET}")
    print(f"{CYAN}{'='*90}{RESET}")

    results = []
    for user in users:
        r = run_user(user)
        results.append(r)
        pen = f" pen={r['penalty_factor']*100:.0f}%"
        budget_str = f" budget={r['total_budget']:.2f}"
        print(f"  {r['user_id']} -> {r['archetype']}  reach={r['reach_score']} adv={r['advocacy_score']} pcu={r['pcu']}{pen}{budget_str}")

    await save_all(results)
    print(f"\n  {GREEN}Saved {len(results)} curves to SQLite{RESET}")

    print_summary(results)

    # Show sample curves
    shown = 0
    for r in results:
        if r["archetype"] in ("Influencer", "Fan") and shown < 2:
            shown += 1
            print(f"\n{BOLD}Sample: {r['label']} ({r['archetype']}) pen={r['penalty_factor']*100:.0f}%{RESET}")
            phases = {}
            for m in r["milestones"]:
                phases.setdefault(m["phase"], []).append(m)
            for pn, ms in phases.items():
                if len(ms) <= 3:
                    for m in ms:
                        print(f"  [{pn}] step {m['step']}: {m['baseline_reward']:.2f}")
                else:
                    print(f"  [{pn}] {len(ms)} steps: {ms[0]['baseline_reward']:.2f} -> {ms[-1]['baseline_reward']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
