"""reward_api.py -- Referral confirmation inbound + reward push outbound.

Connection points for external modules:
- Inbound: confirm_referral() — external referral tracker confirms a referral
- Outbound: set_handler() — register a RewardHandler for reward distribution

Flow:
  1. External tracker calls confirm_referral(user_id, count, timestamp)
  2. API key validated via X-API-Key header
  3. Duplicate check: (user_id, timestamp) in confirmed_referrals → 409
  4. Load pre-saved curve, look up reward for next step
  5. Update user_progress (referrals_completed++, total_earned += reward)
  6. Push RewardEvent to registered handler (default: NoOp logs)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from . import storage
from .reward_handler import RewardEvent, RewardHandler, NoOpRewardHandler
from .config import settings

logger = logging.getLogger("referral_engine.reward_api")

_handler: RewardHandler = NoOpRewardHandler()

ARCHETYPE_LABELS = {
    "Influencer": "Top Referrer",
    "Broadcaster": "Rising Star",
    "Fan": "Loyal User",
    "Newcomer": "Getting Started",
}


def set_handler(handler: RewardHandler) -> None:
    """Register a reward handler for future integration."""
    global _handler
    _handler = handler
    logger.info("Reward handler registered: %s", type(handler).__name__)


async def confirm_referral(user_id: str, count: int = 1, timestamp: str = "") -> dict[str, Any]:
    """Confirm a referral for user_id. External tracker calls this.

    Args:
        user_id: Unique user identifier (verified by external system)
        count: Number of new confirmed referrals (default 1)
        timestamp: ISO-8601 timestamp from external tracker, used for dedup

    Returns:
        {"status": "confirmed"|"new_user"|"completed", "total_earned": float, ...}

    Raises:
        ValueError: if timestamp is missing or referral is a duplicate
        LookupError: if no saved curve found for user_id
    """
    if not timestamp:
        raise ValueError("timestamp from external tracker is required")

    is_dup = await storage.is_duplicate_referral(user_id, timestamp)
    if is_dup:
        raise ValueError(f"Duplicate referral: user={user_id} ts={timestamp}")

    progress = await storage.load_progress(user_id)
    if progress is None:
        curve = await storage.load_curve(user_id)
        if curve is None:
            raise LookupError(f"No saved curve for user '{user_id}'")
        progress = _init_progress(curve)
        await storage.save_progress(user_id, progress)

    new_step = progress["referrals_completed"] + count
    step_rewards = progress.get("curve_step_rewards", {})
    reward_amount = float(step_rewards.get(str(new_step), 0.0))

    updated = await storage.update_referral_progress(user_id, count, reward_amount, count)
    updated["curve_step_rewards"] = step_rewards
    await storage.mark_referral_confirmed(user_id, timestamp, count)

    new_status = "completed" if updated["referrals_completed"] >= updated["referrals_target"] else "confirmed"

    event = RewardEvent(
        user_id=user_id,
        amount=reward_amount,
        unit=updated.get("reward_unit", "points"),
        step=updated["referrals_completed"],
        phase=_phase_for_step(step_rewards, str(updated["referrals_completed"])),
        referrals_completed=updated["referrals_completed"],
        referrals_target=updated["referrals_target"],
        total_earned=updated["total_earned"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    global _handler
    _handler.process(event)

    return {
        "status": new_status,
        "user_id": user_id,
        "referrals_completed": updated["referrals_completed"],
        "referrals_target": updated["referrals_target"],
        "total_earned": updated["total_earned"],
        "reward_for_step": reward_amount,
        "next_step": updated["referrals_completed"] + 1,
        "next_reward": float(step_rewards.get(str(updated["referrals_completed"] + 1), 0.0)),
    }


async def get_user_status(user_id: str) -> dict[str, Any] | None:
    """Get current progress and reward schedule for a user."""
    progress = await storage.load_progress(user_id)
    if progress is None:
        return None
    step_rewards = progress.get("curve_step_rewards", {})
    current = progress["referrals_completed"]
    return {
        "user_id": progress["user_id"],
        "friendly_label": progress["friendly_label"],
        "archetype": progress["archetype"],
        "referrals_completed": current,
        "referrals_target": progress["referrals_target"],
        "total_earned": progress["total_earned"],
        "current_step": progress["current_step"],
        "reward_unit": progress["reward_unit"],
        "penalty_factor": progress["penalty_factor"],
        "status": progress["status"],
        "updated_at": progress["updated_at"],
        "reward_for_step": float(step_rewards.get(str(current), 0.0)),
        "next_reward": float(step_rewards.get(str(current + 1), 0.0)),
        "reasoning": progress.get("reasoning", ""),
    }


def _phase_for_step(step_rewards: dict, step_key: str) -> str:
    return "unknown"


def _init_progress(curve: dict) -> dict[str, Any]:
    milestones = curve.get("milestones", [])
    step_rewards = {}
    phase_map = {}
    for m in milestones:
        s = str(m.get("step", 0))
        r = m.get("baseline_reward", 0)
        step_rewards[s] = r
        phase_map[s] = m.get("phase", "unknown")

    now = datetime.now(timezone.utc).isoformat()
    archetype = curve.get("archetype", "Unknown")

    return {
        "user_id": curve["user_id"],
        "referrals_completed": 0,
        "referrals_target": curve.get("pcu", 0),
        "total_earned": 0.0,
        "current_step": 0,
        "curve_step_rewards": step_rewards,
        "archetype": archetype,
        "friendly_label": ARCHETYPE_LABELS.get(archetype, ""),
        "penalty_factor": curve.get("penalty_factor", 1.0),
        "reward_unit": settings.REWARD_TYPE,
        "status": "active",
        "reasoning": f"Tier={archetype} Reach={curve.get('reach_score',0)} Adv={curve.get('advocacy_score',0)} PCU={curve.get('pcu',0)}",
        "created_at": now,
        "updated_at": now,
    }
