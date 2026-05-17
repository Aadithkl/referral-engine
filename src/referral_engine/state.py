from pydantic import BaseModel


class ReferralState(BaseModel):
    # ── Input ──
    user_id: str = ""
    raw_events: list[dict] = []
    raw_profile: dict = {}

    # ── Signal Parser output (Agent 1) ──
    normalized_profile: dict = {}
    twitter_followers: int = 0
    twitter_engagement: float = 0.0
    account_age_days: int = 0
    last_active_at: str = ""
    prior_referrals: int = 0
    last_asked_at: str = ""
    last_declined_at: str = ""

    # ── Score Calculator output (Agent 2) ──
    reach_score: int = 0
    advocacy_score: int = 0
    pcu: int = 0
    tier: str = ""
    optimal_zone: list[int] = []

    # ── Penalty Calculator output (Agent 3) ──
    should_ask: bool = True
    urgency: float = 0.0
    penalty_factor: float = 1.0
    trigger_detail: str = ""

    # ── Curve Designer output (Agent 4) ──
    hook_reward: float = 0.0
    milestones: list[dict] = []
    total_projected_reward: float = 0.0
    messaging_channel: str = ""
    messaging_tone: str = ""

    # ── Job tracking ──
    job_id: str = ""
    status: str = "queued"
    error: str = ""
    agent_status: list[dict] = []
