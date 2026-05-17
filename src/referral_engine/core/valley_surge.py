"""Ratio-based reward curve math with ramp-down valley phase.

All parameters are unitless ratios anchored to a global BASE_REWARD.
The orchestrating agent assigns the actual unit (dollars, credits, points).

  hook         = BASE_REWARD × HOOK_RATIO
  valley_floor = hook × VALLEY_DROP
  peak         = hook × PEAK_RATIO × urgency

Phase 1 — Hook:         Step 1 = hook reward
Phase 2 — Valley ramp:   Steps 2-3 = linear decline from hook → valley floor
Phase 3 — Valley flat:   Steps 4..4+VALLEY_STEPS-1 = flat at valley floor
Phase 4 — Surge:         After valley to target = linear ramp valley → peak
Phase 5 — Plateau:       Post-target = peak × min(POST_CAP, 1.0 + 0.1×step)
"""

from ..config import settings

QUADRANTS = ["Influencer", "Broadcaster", "Fan", "Newcomer"]
PARAMS = ["HOOK_RATIO", "VALLEY_DROP", "VALLEY_STEPS", "PEAK_RATIO", "POST_CAP"]


def build_curve(quadrant: str, pcu: int, optimal_zone: list[int], urgency: float,
                base_reward: float | None = None) -> tuple[list[dict], float]:
    """Build a ratio-based 5-phase reward curve.

    Args:
        quadrant: User archetype (Influencer, Broadcaster, Fan, Newcomer)
        pcu: Personal Capacity Unit (target referral count)
        optimal_zone: [min, max] range from user's social numbers
        urgency: 0.0-1.0 signal from Orchestrator (scales peak)
        base_reward: Unit anchor (from agent); if None, uses settings.BASE_REWARD

    Returns:
        (milestones, total_budget) where milestones is a list of
        {step, baseline_reward, phase, description}
    """
    if base_reward is None:
        base_reward = settings.BASE_REWARD

    hook_ratio = _get_param(quadrant, "hook_ratio")
    hook = round(base_reward * hook_ratio, 2)

    valley_drop = _get_param(quadrant, "valley_drop")
    valley_steps = int(_get_param(quadrant, "valley_steps"))
    peak_ratio = _get_param(quadrant, "peak_ratio")
    post_cap = _get_param(quadrant, "post_cap")

    valley_floor = round(hook * valley_drop, 2)
    peak = round(hook * peak_ratio * max(urgency, 0.5), 2)

    target = max(1, int(pcu * settings.OPTIMAL_ZONE_PERCENTAGE))

    total_steps = target + 5
    milestones = []
    total_baseline = 0.0

    for step in range(1, total_steps + 1):
        if step == 1:
            reward = hook
            phase = "hook"
        elif step <= 3:
            progress = (step - 1) / 2.0
            reward = round(hook - (hook - valley_floor) * progress, 2)
            phase = "valley"
        elif step <= 3 + valley_steps:
            reward = valley_floor
            phase = "valley"
        elif step <= target:
            surge_progress = step - 3 - valley_steps
            surge_length = max(1, target - 3 - valley_steps)
            ratio = surge_progress / surge_length
            reward = round(valley_floor + (peak - valley_floor) * ratio, 2)
            phase = "surge"
        else:
            plateau_steps = step - target
            reward = round(peak * min(post_cap, 1.0 + 0.1 * plateau_steps), 2)
            phase = "plateau"

        total_baseline += reward

        milestones.append({
            "step": step,
            "baseline_reward": reward,
            "phase": phase,
            "description": _describe(phase, step, target, valley_steps),
        })

    return milestones, round(total_baseline, 2)


def _get_param(quadrant: str, param: str) -> float:
    key = f"{quadrant.upper()}_{param.upper()}"
    val = getattr(settings, key, _defaults().get(key, 0))
    return float(val)


def _defaults() -> dict:
    return {
        "INFLUENCER_HOOK_RATIO": 1.0,
        "INFLUENCER_VALLEY_DROP": 0.25,
        "INFLUENCER_VALLEY_STEPS": 3,
        "INFLUENCER_PEAK_RATIO": 3.0,
        "INFLUENCER_POST_CAP": 2.0,

        "BROADCASTER_HOOK_RATIO": 1.2,
        "BROADCASTER_VALLEY_DROP": 0.10,
        "BROADCASTER_VALLEY_STEPS": 4,
        "BROADCASTER_PEAK_RATIO": 2.5,
        "BROADCASTER_POST_CAP": 1.3,

        "FAN_HOOK_RATIO": 0.6,
        "FAN_VALLEY_DROP": 0.70,
        "FAN_VALLEY_STEPS": 1,
        "FAN_PEAK_RATIO": 1.5,
        "FAN_POST_CAP": 1.5,

        "NEWCOMER_HOOK_RATIO": 0.4,
        "NEWCOMER_VALLEY_DROP": 0.25,
        "NEWCOMER_VALLEY_STEPS": 3,
        "NEWCOMER_PEAK_RATIO": 2.0,
        "NEWCOMER_POST_CAP": 1.2,
    }


def _describe(phase: str, step: int, target: int, valley: int) -> str:
    if phase == "hook":
        return f"Step 1: Instant sign-up reward"
    if phase == "valley":
        return f"Step {step}: Valley (ramp-down)" if step <= 3 else f"Step {step}: Valley (flat, {step - 3}/{valley})"
    if phase == "surge":
        return f"Step {step}: Ramp toward target of {target}"
    return f"Step {step}: Post-target capped reward"
