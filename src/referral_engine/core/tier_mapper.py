"""Score-to-archetype mapping using binary split thresholds."""

from ..config import settings


def classify_quadrant(reach: int, advocacy: int) -> str:
    """Classify user into one of 4 archetypes based on binary reach/advocacy split."""
    high_reach = reach > settings.QUADRANT_REACH_SPLIT
    high_adv = advocacy > settings.QUADRANT_ADVOCACY_SPLIT

    if high_reach and high_adv:
        return "Influencer"
    if high_reach and not high_adv:
        return "Broadcaster"
    if not high_reach and high_adv:
        return "Fan"
    return "Newcomer"


def classify_tier(reach: int, advocacy: int) -> tuple[str, str]:
    """Backward-compat: return archetype + justification string."""
    archetype = classify_quadrant(reach, advocacy)
    high_reach = reach > settings.QUADRANT_REACH_SPLIT
    high_adv = advocacy > settings.QUADRANT_ADVOCACY_SPLIT
    justification = (
        f"Archetype={archetype}: Reach={reach}({'high' if high_reach else 'low'}), "
        f"Advocacy={advocacy}({'high' if high_adv else 'low'})"
    )
    return archetype, justification


def get_tier_budget(tier: str) -> float:
    """Return a default budget multiplier for a given archetype tier."""
    multipliers = {
        "Influencer": 5000.0,
        "Broadcaster": 2000.0,
        "Fan": 500.0,
        "Newcomer": 100.0,
    }
    return multipliers.get(tier, 100.0)
