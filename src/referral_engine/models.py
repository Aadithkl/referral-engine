from pydantic import BaseModel
from typing import Optional


class NormalizedProfile(BaseModel):
    account_age_days: int
    last_active_at: Optional[str] = None
    total_product_sessions_90d: int = 0
    feature_adoption_count: int = 0
    support_tickets_90d: int = 0
    support_tickets_resolved: int = 0
    positive_outcome_events: int = 0
    recent_activity_trend: str = "stable"
    twitter_handle: Optional[str] = None
    twitter_followers: int = 0
    twitter_following: int = 0
    twitter_tweet_count: int = 0
    twitter_engagement_rate: float = 0.0
    prior_referrals_total: int = 0
    last_asked_at: Optional[str] = None
    last_declined_at: Optional[str] = None


class ScoreOutput(BaseModel):
    reach_score: int
    advocacy_score: int
    pcu: int
    tier: str
    optimal_zone: list[int]
    reasoning: str


class AskDecision(BaseModel):
    should_ask: bool
    urgency: float
    reasoning: str


class CurvePlan(BaseModel):
    hook_reward: float
    milestones: list[dict]
    total_reward: float
    channel: str
    tone: str
    strategy_note: str
    summary: str = ""


class AnalyzeRequest(BaseModel):
    user_id: str
    source: str = "product_backend"
    data: dict = {}
    callback_url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    estimated_time: str = "10-15s"
