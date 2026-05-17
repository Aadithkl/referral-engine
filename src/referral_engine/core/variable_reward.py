"""Variable reward distribution (loot box mechanics).

Each milestone's baseline reward is wrapped in a random distribution:
  - Floor: VARIANCE_FLOOR % of baseline (default 75%)
  - Ceiling: VARIANCE_CEILING % of baseline (default 140%)
  - Jackpot: JACKPOT_CHANCE % chance of JACKPOT_MULTIPLIER x payout (default 5% chance of 3x)

This creates "Mega Wins" and "Jackpots" for dopamine-driven habituation.
"""

import random

from ..config import settings


def apply_variable_layer(baseline: float, seed: int | None = None) -> tuple[float, str]:
    """Apply variable reward layer to a baseline amount.

    Args:
        baseline: The deterministic baseline reward
        seed: Optional random seed for reproducibility (testing)

    Returns:
        (reward, reward_type) where type is 'normal', 'mega_win', or 'jackpot'
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    # Check jackpot first
    if rng.random() < settings.JACKPOT_CHANCE:
        reward = baseline * settings.JACKPOT_MULTIPLIER
        return round(reward, 2), "jackpot"

    # Normal range with variable multiplier
    multiplier = rng.uniform(settings.VARIANCE_FLOOR, settings.VARIANCE_CEILING)
    reward = baseline * multiplier

    # Classify as mega_win if in top 10% of range
    top_threshold = settings.VARIANCE_FLOOR + 0.9 * (
        settings.VARIANCE_CEILING - settings.VARIANCE_FLOOR
    )
    reward_type = "mega_win" if multiplier >= top_threshold else "normal"

    return round(reward, 2), reward_type


def apply_to_curve(
    milestones: list[dict], seed: int | None = None
) -> list[dict]:
    """Apply variable reward layer to every milestone in a curve.

    Returns milestones with added 'variable_reward' and 'reward_type' fields.
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    enriched = []
    for m in milestones:
        var_reward, rtype = apply_variable_layer(
            m["baseline_reward"], seed=rng.randint(0, 999999)
        )
        enriched.append({
            **m,
            "variable_reward": var_reward,
            "reward_type": rtype,
        })
    return enriched
