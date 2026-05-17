"""penalty.py -- Penalty factor computation from gate thresholds.

Converts the 5 legacy gate checks into a penalty multiplier (0.05–1.0)
that scales curve rewards for low-metric users.
"""

from datetime import datetime, timedelta, timezone
from ..config import settings


def compute_penalty(
    age_days: int,
    advocacy: int,
    tickets_count: int,
    tickets_resolved: int,
    last_asked: str | None = None,
    last_declined: str | None = None,
) -> tuple[float, list[str]]:
    """Compute penalty factor from 5 gate checks. Returns (factor, reasons).

    Penalty ranges from PENALTY_FLOOR_GLOBAL (0.05) to 1.0.
    1.0 = perfect user, no penalty. Lower = scaled-down rewards.
    """
    reasons = []
    penalties = []

    # 1. Advocacy
    p_adv = max(settings.PENALTY_FLOOR_ADVOCACY, advocacy / max(1, settings.MIN_ADVOCACY_FOR_ASK))
    p_adv = min(1.0, p_adv)
    if p_adv < 1.0:
        reasons.append(f"adv={advocacy}/{settings.MIN_ADVOCACY_FOR_ASK} pen={p_adv:.2f}")
    penalties.append(p_adv)

    # 2. Account age
    p_age = max(settings.PENALTY_FLOOR_AGE, age_days / max(1, settings.MIN_ACCOUNT_AGE_DAYS))
    p_age = min(1.0, p_age)
    if p_age < 1.0:
        reasons.append(f"age={age_days}/{settings.MIN_ACCOUNT_AGE_DAYS}d pen={p_age:.2f}")
    penalties.append(p_age)

    # 3. Unresolved tickets
    unresolved = tickets_count - tickets_resolved
    p_tix = max(settings.PENALTY_FLOOR_TICKETS, 1.0 / (1 + unresolved))
    p_tix = min(1.0, p_tix)
    if p_tix < 1.0:
        reasons.append(f"tickets_unresolved={unresolved} pen={p_tix:.2f}")
    penalties.append(p_tix)

    # 4. Ask cooldown
    p_ask = 1.0
    if last_asked:
        try:
            asked_date = datetime.fromisoformat(last_asked.replace("Z", "+00:00"))
            next_allowed = asked_date + timedelta(days=settings.ASK_COOLDOWN_DAYS)
            now = datetime.now(timezone.utc)
            if now < next_allowed:
                days_total = settings.ASK_COOLDOWN_DAYS
                days_left = (next_allowed - now).days
                days_elapsed = days_total - max(days_left, 0)
                p_ask = max(0.10, days_elapsed / max(1, days_total))
                reasons.append(f"ask_cd={days_left}d left pen={p_ask:.2f}")
        except (ValueError, AttributeError):
            pass
    penalties.append(p_ask)

    # 5. Decline cooldown
    p_dec = 1.0
    if last_declined:
        try:
            declined_date = datetime.fromisoformat(last_declined.replace("Z", "+00:00"))
            next_allowed = declined_date + timedelta(days=settings.DECLINED_ASK_COOLDOWN_DAYS)
            now = datetime.now(timezone.utc)
            if now < next_allowed:
                days_total = settings.DECLINED_ASK_COOLDOWN_DAYS
                days_left = (next_allowed - now).days
                days_elapsed = days_total - max(days_left, 0)
                p_dec = max(0.10, days_elapsed / max(1, days_total))
                reasons.append(f"decline_cd={days_left}d left pen={p_dec:.2f}")
        except (ValueError, AttributeError):
            pass
    penalties.append(p_dec)

    factor = 1.0
    for p in penalties:
        factor *= p
    factor = max(settings.PENALTY_FLOOR_GLOBAL, min(1.0, factor))
    factor = round(factor, 4)

    if not reasons:
        reasons.append("all checks passed, no penalty")
    else:
        reasons.append(f"combined={factor:.2f}")

    return factor, reasons
