"""Show penalties and curves for personas."""
import sys; sys.path.insert(0, 'src')

from referral_engine.core.valley_surge import build_curve
from referral_engine.core.variable_reward import apply_to_curve
from referral_engine.core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from referral_engine.core.tier_mapper import classify_tier
from referral_engine.core.penalty import compute_penalty
from referral_engine.config import settings

tests = [
    ("Power User (Broadcaster)", 5000, 0.052, 1200, 607, 95, 8, 15, 1, 1, "rising"),
    ("Builder",                 10,   0.005, 100,  620, 72, 6, 9,  2, 2, "rising"),
]

for name, f, tw_e, tw_f, age, ses, feat, out, tix, res, trend in tests:
    reach, _ = compute_reach(f, tw_e, tw_f, age)
    adv, _ = compute_advocacy(ses, feat, out, tix, res, trend)
    pcu, _ = compute_pcu(f, age, adv)
    tier, _ = classify_tier(reach, adv)
    penalty, reasons = compute_penalty(age, adv, tix, res)

    penalized_base = settings.BASE_REWARD * penalty
    urgency = min(1.0, adv / 100.0)
    milestones, total = build_curve(tier, pcu, [1, pcu], max(urgency, 0.5), base_reward=penalized_base)
    enriched = apply_to_curve(milestones, seed=42)

    print()
    print("=" * 60)
    print(f"  {name}")
    print("=" * 60)
    print(f"  Scores: reach={reach}  adv={adv}  pcu={pcu}")
    print(f"  Archetype: {tier}")
    print(f"  Penalty: {penalty:.4f} ({penalty*100:.0f}%)")
    for r in reasons:
        print(f"    {r}")
    print(f"  Curve:  total={total:,.2f}  steps={len(enriched)}")

    phases = {"hook": [], "valley": [], "surge": [], "plateau": []}
    for m in enriched:
        phases[m["phase"]].append(m)
    for pn, ms in phases.items():
        if not ms:
            continue
        print(f"  [{pn.upper()}]")
        for m in ms:
            tag = ""
            if m["reward_type"] == "jackpot":
                tag = "  *** JACKPOT"
            elif m["reward_type"] == "mega_win":
                tag = "  ** mega"
            print(f"    step {m['step']:3d}:  {m['baseline_reward']:>8.2f}  ->  {m['variable_reward']:>8.2f}{tag}")

print()
print("=" * 60)
print(f"  Config: JACKPOT={settings.JACKPOT_MULTIPLIER}x at {int(settings.JACKPOT_CHANCE*100)}%  variance={settings.VARIANCE_FLOOR}-{settings.VARIANCE_CEILING}")
print(f"          reach_split={settings.QUADRANT_REACH_SPLIT}  adv_split={settings.QUADRANT_ADVOCACY_SPLIT}")
print(f"          penalty_floor_global={settings.PENALTY_FLOOR_GLOBAL}")
