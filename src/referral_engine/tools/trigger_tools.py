"""CrewAI @tool wrappers for trigger evaluation and gate checking.

These tools wrap deterministic logic from core/ and .env thresholds
to evaluate when a user should be asked for a referral.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from crewai.tools import tool
from ..config import settings


@tool("TriggerEvaluatorTool")
def trigger_evaluator_tool(
    normalized_profile: dict,
    reach_score: int,
    advocacy_score: int,
    prior_referrals: int,
    last_asked_at: str = "",
    last_declined_at: str = "",
) -> dict:
    """Evaluate all trigger conditions using parsed data and scores.

    Returns {triggers_found: list[str], confidence: float, detail: str}.
    """
    triggers_found = []
    confidence = 0.0

    # Trigger 1: High advocacy users are primed
    if advocacy_score >= settings.MIN_ADVOCACY_FOR_ASK:
        triggers_found.append("high_advocacy")
        confidence += 0.3

    # Trigger 2: Recent positive activity trend
    trend = normalized_profile.get("recent_activity_trend", "stable")
    if trend == "rising":
        triggers_found.append("rising_activity")
        confidence += 0.25
    elif trend == "stable":
        confidence += 0.1

    # Trigger 3: Support tickets all resolved
    tickets = normalized_profile.get("support_tickets_90d", 0)
    resolved = normalized_profile.get("support_tickets_resolved", 0)
    if tickets > 0 and tickets == resolved:
        triggers_found.append("all_tickets_resolved")
        confidence += 0.2

    # Trigger 4: Account age sufficient
    age_days = normalized_profile.get("account_age_days", 0)
    if age_days >= settings.MIN_ACCOUNT_AGE_DAYS:
        triggers_found.append("mature_account")
        confidence += 0.15

    # Trigger 5: Has social presence (higher reach)
    if reach_score >= 40:
        triggers_found.append("social_presence")
        confidence += 0.1

    confidence = min(1.0, round(confidence, 2))

    return {
        "triggers_found": triggers_found,
        "confidence": confidence,
        "detail": f"Triggers: {', '.join(triggers_found) if triggers_found else 'none'}, confidence={confidence}",
    }


@tool("GateCheckerTool")
def gate_checker_tool(
    account_age_days: int,
    advocacy_score: int,
    support_tickets_90d: int,
    support_tickets_resolved: int,
    last_declined_at: str = "",
) -> dict:
    """Check all cooldown gates against .env thresholds.

    Returns {gates_checked, gates_passed, gates_blocked}.
    """
    gates_checked = ["account_age", "advocacy_minimum", "support_cooldown", "declined_cooldown"]
    gates_passed = []
    gates_blocked = []

    # Gate 1: Account age minimum
    if account_age_days >= settings.MIN_ACCOUNT_AGE_DAYS:
        gates_passed.append("account_age")
    else:
        gates_blocked.append(f"account_age: {account_age_days}d < {settings.MIN_ACCOUNT_AGE_DAYS}d min")

    # Gate 2: Advocacy minimum
    if advocacy_score >= settings.MIN_ADVOCACY_FOR_ASK:
        gates_passed.append("advocacy_minimum")
    else:
        gates_blocked.append(f"advocacy_minimum: {advocacy_score} < {settings.MIN_ADVOCACY_FOR_ASK}")

    # Gate 3: Support ticket cooldown
    if support_tickets_90d == 0 or support_tickets_90d == support_tickets_resolved:
        gates_passed.append("support_cooldown")
    else:
        gates_blocked.append(f"support_cooldown: {support_tickets_90d - support_tickets_resolved} unresolved tickets")

    # Gate 4: Declined ask cooldown
    if last_declined_at and last_declined_at.strip():
        try:
            declined_date = datetime.fromisoformat(last_declined_at.replace("Z", "+00:00"))
            cooldown_end = declined_date + timedelta(days=settings.DECLINED_ASK_COOLDOWN_DAYS)
            if datetime.now(timezone.utc) > cooldown_end:
                gates_passed.append("declined_cooldown")
            else:
                gates_blocked.append(f"declined_cooldown: cooldown until {cooldown_end.isoformat()}")
        except (ValueError, AttributeError):
            gates_passed.append("declined_cooldown")  # unparseable date, let it through
    else:
        gates_passed.append("declined_cooldown")

    return {
        "gates_checked": gates_checked,
        "gates_passed": gates_passed,
        "gates_blocked": gates_blocked,
    }


@tool("UserStateQueryTool")
def user_state_query_tool(user_id: str) -> dict:
    """Fetch current user state from referral_plans for gate context.

    In production this queries PostgreSQL. For now, returns empty defaults.
    """
    return {
        "user_id": user_id,
        "has_existing_plan": False,
        "last_plan_status": None,
        "active_referrals_count": 0,
    }
