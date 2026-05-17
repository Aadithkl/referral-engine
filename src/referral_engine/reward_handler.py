"""reward_handler.py -- Pluggable reward handler interface for future integration.

Defines the RewardHandler Protocol that external reward distribution modules
must implement. Default NoOpRewardHandler logs events as documentation.

Future integrations can register any handler implementing the Protocol:
  from referral_engine.reward_handler import RewardHandler, NoOpRewardHandler
  class CreditsHandler(RewardHandler):
      def process(self, event): ...
  reward_api.set_handler(CreditsHandler())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger("referral_engine.reward_handler")


@dataclass
class RewardEvent:
    """Payload pushed to reward handler after referral confirmation."""

    user_id: str
    amount: float
    unit: str
    step: int
    phase: str
    referrals_completed: int
    referrals_target: int
    total_earned: float
    timestamp: str
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class RewardHandler(Protocol):
    """Protocol that external reward distribution modules must implement.

    Registrable via reward_api.set_handler(instance).
    Called synchronously after each confirmed referral.
    """

    def process(self, event: RewardEvent) -> bool:
        """Process a reward event. Return True on success.

        Must be idempotent — reward_api deduplicates before calling this.
        """
        ...


class NoOpRewardHandler:
    """Default handler that logs events. Placeholder for future integration.

    Usage: import and register your handler that conforms to RewardHandler Protocol.
    """

    def process(self, event: RewardEvent) -> bool:
        logger.info(
            "[REWARD HANDLER] user=%s step=%d amount=%.2f %s total_earned=%.2f phase=%s",
            event.user_id, event.step, event.amount, event.unit,
            event.total_earned, event.phase,
        )
        return True
