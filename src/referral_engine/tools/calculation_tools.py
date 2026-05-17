"""CrewAI @tool wrappers for scoring, tier mapping, curve building, and reward.

These tools wrap the deterministic core/ functions so the LLM can call them
via CrewAI's tool-calling mechanism. The LLM sees tool signatures; the math
executes deterministically.
"""

from crewai.tools import tool

from ..core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from ..core.tier_mapper import classify_tier, get_tier_budget
from ..core.valley_surge import build_curve
from ..core.variable_reward import apply_variable_layer, apply_to_curve
from ..config import settings


@tool("CalculationTool")
def calculation_tool(
    twitter_followers: int,
    twitter_engagement: float,
    twitter_following: int,
    account_age_days: int,
    total_sessions_90d: int,
    feature_adoption: int,
    positive_outcomes: int,
    support_tickets: int,
    support_resolved: int,
    activity_trend: str,
) -> dict:
    """Compute Reach, Advocacy, and PCU scores from user data.

    Applies weights from .env: REACH_FOLLOWER_WEIGHT, REACH_ENGAGEMENT_WEIGHT, etc.
    Returns {reach, advocacy, pcu, reach_reasoning, advocacy_reasoning, pcu_reasoning}.
    """
    reach, reach_reason = compute_reach(
        twitter_followers, twitter_engagement, twitter_following, account_age_days
    )
    advocacy, adv_reason = compute_advocacy(
        total_sessions_90d, feature_adoption, positive_outcomes,
        support_tickets, support_resolved, activity_trend,
    )
    pcu, pcu_reason = compute_pcu(twitter_followers, account_age_days, advocacy)

    return {
        "reach": reach,
        "advocacy": advocacy,
        "pcu": pcu,
        "reach_reasoning": reach_reason,
        "advocacy_reasoning": adv_reason,
        "pcu_reasoning": pcu_reason,
    }


@tool("TierMapperTool")
def tier_mapper_tool(reach: int, advocacy: int) -> dict:
    """Map Reach and Advocacy scores to a user tier using thresholds from .env.
    Returns {tier, justification, budget}.
    """
    tier, justification = classify_tier(reach, advocacy)
    budget = get_tier_budget(tier)
    return {"tier": tier, "justification": justification, "budget": budget}


@tool("ValleySurgeCalculatorTool")
def valley_surge_calculator_tool(
    tier: str, pcu: int, optimal_zone_min: int, optimal_zone_max: int, urgency: float
) -> dict:
    """Build a personalized Valley & Surge reward curve.

    Uses HOOK_REWARD, VALLEY_FLOOR, VALLEY_STEPS, SURGE_EXPONENT from .env.
    Returns {curve: list[dict], total_budget: float}.
    """
    milestones, total_budget = build_curve(
        tier, pcu, [optimal_zone_min, optimal_zone_max], urgency
    )
    return {"curve": milestones, "total_budget": total_budget}


@tool("VariableRewardTool")
def variable_reward_tool(baseline: float) -> dict:
    """Apply variable reward layer (loot box) to a baseline reward.

    Uses VARIANCE_FLOOR, VARIANCE_CEILING, JACKPOT_CHANCE, JACKPOT_MULTIPLIER from .env.
    Returns {reward: float, type: str} — type is 'normal', 'mega_win', or 'jackpot'.
    """
    reward, rtype = apply_variable_layer(baseline)
    return {"reward": reward, "type": rtype}


@tool("StrategySelectorTool")
def strategy_selector_tool(
    tier: str, twitter_engagement: float, urgency: float,
    normalized_profile: dict,
) -> dict:
    """Select messaging channel and tone based on user profile and urgency.

    Returns {channel: str, tone: str, reasoning: str}.
    """
    # Channel selection logic
    if urgency > 0.7:
        channel = "push"
    elif twitter_engagement > 0.03 and urgency > 0.4:
        channel = "twitter_dm"
    elif urgency > 0.3:
        channel = "in-app"
    else:
        channel = "email"

    # Tone selection logic
    if urgency > 0.8:
        tone = "urgent"
    elif urgency > 0.5:
        tone = "opportunity"
    else:
        tone = "gentle_nudge"

    reasoning = (
        f"Strategy: channel={channel}, tone={tone} "
        f"(urgency={urgency:.2f}, engagement={twitter_engagement:.4f}, tier={tier})"
    )

    return {"channel": channel, "tone": tone, "reasoning": reasoning}
