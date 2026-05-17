"""Deterministic scoring formulas for Reach, Advocacy, and PCU.

All weights and thresholds come from config.settings (loaded from .env).
"""

import math
from ..config import settings


def _normalize(value: float, benchmark: float, cap: float = 100.0) -> float:
    """Normalize a value against a benchmark, capped at 100."""
    if benchmark <= 0:
        return 0.0
    return min(cap, (value / benchmark) * 100.0)


def compute_reach(
    twitter_followers: int,
    twitter_engagement: float,
    twitter_following: int,
    account_age_days: int,
) -> tuple[int, str]:
    """Compute Reach score (0-100) from social signals.

    Weighted combination of:
    - Follower count (normalized by log scale)
    - Engagement rate (normalized by benchmark)
    - Network relevance (following/follower ratio inverted)

    Returns (score, reasoning).
    """
    # Follower score: log-normalized, 100 followers = 30, 1000 = 60, 10000 = 90
    if twitter_followers <= 0:
        follower_score = 0.0
    else:
        follower_score = min(100.0, math.log10(twitter_followers + 1) * 25.0)

    # Engagement score: normalized by benchmark
    engagement_score = _normalize(
        twitter_engagement,
        settings.BENCHMARK_ENGAGEMENT_RATE,
    )

    # Relevance score: based on following/follower ratio (balanced networks score higher)
    if twitter_followers > 0:
        ratio = twitter_following / max(twitter_followers, 1)
        if ratio <= 1.0:
            relevance = 100.0
        elif ratio <= 5.0:
            relevance = 60.0
        else:
            relevance = 20.0
    elif account_age_days > 30:
        relevance = 30.0  # long-term user with no social is mid
    else:
        relevance = 10.0  # new user, no social

    # Weighted combination
    score = (
        settings.REACH_FOLLOWER_WEIGHT * follower_score
        + settings.REACH_ENGAGEMENT_WEIGHT * engagement_score
        + settings.REACH_RELEVANCE_WEIGHT * relevance
    )

    score = int(round(min(100.0, max(0.0, score))))

    reasoning = (
        f"Reach={score}: followers={twitter_followers}(log={follower_score:.1f}), "
        f"engagement={twitter_engagement:.4f}(norm={engagement_score:.1f}), "
        f"relevance={relevance:.1f}"
    )

    return score, reasoning


def compute_advocacy(
    total_sessions_90d: int,
    feature_adoption: int,
    positive_outcomes: int,
    support_tickets: int,
    support_resolved: int,
    activity_trend: str,
) -> tuple[int, str]:
    """Compute Advocacy score (0-100) from in-product behavior.

    Weighted combination of:
    - Usage depth (sessions, feature adoption)
    - Outcome quality (positive events, resolved tickets)
    - Activity trend (rising/stable/declining)
    - Sentiment (ticket resolution rate)

    Returns (score, reasoning).
    """
    # Usage score: sessions normalized (100 sessions = full)
    usage_score = _normalize(total_sessions_90d, 100.0)

    # Feature adoption: 5 features = reasonable, 10+ = power user
    feature_score = _normalize(feature_adoption, 10.0)

    # Outcome score: positive events normalized
    outcome_score = _normalize(positive_outcomes, 20.0)

    # Sentiment score: ticket resolution rate
    if support_tickets > 0:
        resolution_rate = support_resolved / support_tickets
        sentiment_score = resolution_rate * 100.0
    else:
        sentiment_score = 70.0  # neutral default, no tickets

    sentiment_score = min(100.0, sentiment_score)

    # Trend multiplier
    trend_map = {"rising": 1.15, "stable": 1.0, "declining": 0.7}
    trend_mult = trend_map.get(activity_trend, 1.0)

    # Weighted combination
    score = (
        settings.ADVOCACY_USAGE_WEIGHT * usage_score
        + settings.ADVOCACY_TREND_WEIGHT * (usage_score * trend_mult)
        + settings.ADVOCACY_OUTCOME_WEIGHT * outcome_score
        + settings.ADVOCACY_SENTIMENT_WEIGHT * sentiment_score
    )

    score = int(round(min(100.0, max(0.0, score))))

    reasoning = (
        f"Advocacy={score}: sessions={total_sessions_90d}(usage={usage_score:.1f}), "
        f"features={feature_adoption}({feature_score:.1f}), "
        f"outcomes={positive_outcomes}({outcome_score:.1f}), "
        f"sentiment={sentiment_score:.1f}(tickets={support_tickets}/{support_resolved}), "
        f"trend={activity_trend}(x{trend_mult})"
    )

    return score, reasoning


def compute_pcu(
    twitter_followers: int,
    account_age_days: int,
    advocacy_score: int,
) -> tuple[int, str]:
    """Compute Personal Capacity Unit (optimal referral target).

    Combines reach potential with user's demonstrated loyalty/advocacy
    to estimate how many successful referrals the user can realistically make.

    Returns (pcu, reasoning).
    """
    # Public post reach: followers * conversion rate
    public_reach = twitter_followers * settings.PCU_PUBLIC_POST_CONVERSION

    # Community reach: estimated community size based on followers
    community_estimate = max(0, twitter_followers * 0.1)
    community_reach = community_estimate * settings.PCU_COMMUNITY_CONVERSION

    # Direct message: estimate based on followers and advocacy
    dm_pool = max(0, twitter_followers * 0.02)
    dm_reach = dm_pool * settings.PCU_DIRECT_MESSAGE_CONVERSION

    # Base PCU from reach
    base_pcu = public_reach + community_reach + dm_reach

    # Advocacy modifier: higher advocacy = more effective referrals
    advocacy_mod = 0.5 + (advocacy_score / 200.0)  # 0.5 to 1.0 range

    # Account age modifier: older accounts have more established networks
    age_mod = min(1.2, 0.7 + (account_age_days / 365.0) * 0.5)  # 0.7 to 1.2

    pcu = int(round(base_pcu * advocacy_mod * age_mod))
    pcu = max(1, pcu)  # minimum 1 referral

    reasoning = (
        f"PCU={pcu}: public={public_reach:.1f}(followers={twitter_followers}x{settings.PCU_PUBLIC_POST_CONVERSION}), "
        f"community={community_reach:.1f}, DM={dm_reach:.1f}, "
        f"advocacy_mod={advocacy_mod:.2f}, age_mod={age_mod:.2f}"
    )

    return pcu, reasoning
