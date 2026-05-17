import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ─── API & LLM ───
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

    # ─── DATABASE ───
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/referral_engine")

    # ─── TWITTER API ───
    TWITTER_CLIENT_ID: str = os.getenv("TWITTER_CLIENT_ID", "")
    TWITTER_CLIENT_SECRET: str = os.getenv("TWITTER_CLIENT_SECRET", "")
    TWITTER_REDIRECT_URI: str = os.getenv("TWITTER_REDIRECT_URI", "")

    # ─── WEBHOOK SECURITY ───
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    WEBHOOK_SIGNATURE_HEADER: str = os.getenv("WEBHOOK_SIGNATURE_HEADER", "X-Signature")

    # ─── REWARD SYSTEM ───
    REWARD_TYPE: str = os.getenv("REWARD_TYPE", "cash")
    BASE_REWARD: float = float(os.getenv("BASE_REWARD", "10"))

    # ─── CURVE ARCHETYPES (pure ratios, unitless — agent assigns actual unit) ───
    # Influencer: high reach + high advocacy — med hook, moderate valley, slow surge
    INFLUENCER_HOOK_RATIO: float = float(os.getenv("INFLUENCER_HOOK_RATIO", "1.0"))
    INFLUENCER_VALLEY_DROP: float = float(os.getenv("INFLUENCER_VALLEY_DROP", "0.25"))
    INFLUENCER_VALLEY_STEPS: float = float(os.getenv("INFLUENCER_VALLEY_STEPS", "3"))
    INFLUENCER_PEAK_RATIO: float = float(os.getenv("INFLUENCER_PEAK_RATIO", "3.0"))
    INFLUENCER_POST_CAP: float = float(os.getenv("INFLUENCER_POST_CAP", "2.0"))

    # Broadcaster: high reach + low advocacy — big hook, steep valley, slow climb
    BROADCASTER_HOOK_RATIO: float = float(os.getenv("BROADCASTER_HOOK_RATIO", "1.2"))
    BROADCASTER_VALLEY_DROP: float = float(os.getenv("BROADCASTER_VALLEY_DROP", "0.10"))
    BROADCASTER_VALLEY_STEPS: float = float(os.getenv("BROADCASTER_VALLEY_STEPS", "4"))
    BROADCASTER_PEAK_RATIO: float = float(os.getenv("BROADCASTER_PEAK_RATIO", "2.5"))
    BROADCASTER_POST_CAP: float = float(os.getenv("BROADCASTER_POST_CAP", "1.3"))

    # Fan: low reach + high advocacy — med-low hook, shallow valley, fast to target
    FAN_HOOK_RATIO: float = float(os.getenv("FAN_HOOK_RATIO", "0.6"))
    FAN_VALLEY_DROP: float = float(os.getenv("FAN_VALLEY_DROP", "0.70"))
    FAN_VALLEY_STEPS: float = float(os.getenv("FAN_VALLEY_STEPS", "1"))
    FAN_PEAK_RATIO: float = float(os.getenv("FAN_PEAK_RATIO", "1.5"))
    FAN_POST_CAP: float = float(os.getenv("FAN_POST_CAP", "1.5"))

    # Newcomer: low reach + low advocacy — low hook, moderate valley, slow surge
    NEWCOMER_HOOK_RATIO: float = float(os.getenv("NEWCOMER_HOOK_RATIO", "0.4"))
    NEWCOMER_VALLEY_DROP: float = float(os.getenv("NEWCOMER_VALLEY_DROP", "0.25"))
    NEWCOMER_VALLEY_STEPS: float = float(os.getenv("NEWCOMER_VALLEY_STEPS", "3"))
    NEWCOMER_PEAK_RATIO: float = float(os.getenv("NEWCOMER_PEAK_RATIO", "2.0"))
    NEWCOMER_POST_CAP: float = float(os.getenv("NEWCOMER_POST_CAP", "1.2"))

    # ─── VARIABLE REWARD ───
    VARIANCE_FLOOR: float = float(os.getenv("VARIANCE_FLOOR", "0.75"))
    VARIANCE_CEILING: float = float(os.getenv("VARIANCE_CEILING", "1.4"))
    JACKPOT_CHANCE: float = float(os.getenv("JACKPOT_CHANCE", "0.05"))
    JACKPOT_MULTIPLIER: float = float(os.getenv("JACKPOT_MULTIPLIER", "3.0"))

    # ─── SCORING WEIGHTS ───
    REACH_FOLLOWER_WEIGHT: float = float(os.getenv("REACH_FOLLOWER_WEIGHT", "0.4"))
    REACH_ENGAGEMENT_WEIGHT: float = float(os.getenv("REACH_ENGAGEMENT_WEIGHT", "0.35"))
    REACH_RELEVANCE_WEIGHT: float = float(os.getenv("REACH_RELEVANCE_WEIGHT", "0.25"))
    ADVOCACY_USAGE_WEIGHT: float = float(os.getenv("ADVOCACY_USAGE_WEIGHT", "0.4"))
    ADVOCACY_TREND_WEIGHT: float = float(os.getenv("ADVOCACY_TREND_WEIGHT", "0.2"))
    ADVOCACY_OUTCOME_WEIGHT: float = float(os.getenv("ADVOCACY_OUTCOME_WEIGHT", "0.25"))
    ADVOCACY_SENTIMENT_WEIGHT: float = float(os.getenv("ADVOCACY_SENTIMENT_WEIGHT", "0.15"))

    # ─── TIER THRESHOLDS ───
    REACH_LOW_MAX: int = int(os.getenv("REACH_LOW_MAX", "33"))
    REACH_MID_MAX: int = int(os.getenv("REACH_MID_MAX", "66"))
    ADVOCACY_LOW_MAX: int = int(os.getenv("ADVOCACY_LOW_MAX", "33"))
    ADVOCACY_MID_MAX: int = int(os.getenv("ADVOCACY_MID_MAX", "66"))
    QUADRANT_REACH_SPLIT: int = int(os.getenv("QUADRANT_REACH_SPLIT", "50"))
    QUADRANT_ADVOCACY_SPLIT: int = int(os.getenv("QUADRANT_ADVOCACY_SPLIT", "50"))

    # ─── RAW INPUT THRESHOLDS (for classification display) ───
    RAW_FOLLOWERS_HIGH: int = int(os.getenv("RAW_FOLLOWERS_HIGH", "1500"))
    RAW_ENGAGEMENT_HIGH: float = float(os.getenv("RAW_ENGAGEMENT_HIGH", "0.01"))
    RAW_SESSIONS_HIGH: int = int(os.getenv("RAW_SESSIONS_HIGH", "50"))
    RAW_FEATURES_HIGH: int = int(os.getenv("RAW_FEATURES_HIGH", "5"))

    # ─── CAPACITY CALCULATION ───
    PCU_PUBLIC_POST_CONVERSION: float = float(os.getenv("PCU_PUBLIC_POST_CONVERSION", "0.008"))
    PCU_COMMUNITY_CONVERSION: float = float(os.getenv("PCU_COMMUNITY_CONVERSION", "0.035"))
    PCU_DIRECT_MESSAGE_CONVERSION: float = float(os.getenv("PCU_DIRECT_MESSAGE_CONVERSION", "0.25"))
    OPTIMAL_ZONE_PERCENTAGE: float = float(os.getenv("OPTIMAL_ZONE_PERCENTAGE", "0.75"))

    # ─── TRIGGER GATES ───
    MIN_ADVOCACY_FOR_ASK: int = int(os.getenv("MIN_ADVOCACY_FOR_ASK", "50"))
    MIN_ACCOUNT_AGE_DAYS: int = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", "14"))
    MAX_UNRESOLVED_TICKETS: int = int(os.getenv("MAX_UNRESOLVED_TICKETS", "0"))
    ASK_COOLDOWN_DAYS: int = int(os.getenv("ASK_COOLDOWN_DAYS", "30"))
    SUPPORT_TICKET_WINDOW_DAYS: int = int(os.getenv("SUPPORT_TICKET_WINDOW_DAYS", "90"))
    SUPPORT_TICKET_COOLDOWN_DAYS: int = int(os.getenv("SUPPORT_TICKET_COOLDOWN_DAYS", "7"))
    DECLINED_ASK_COOLDOWN_DAYS: int = int(os.getenv("DECLINED_ASK_COOLDOWN_DAYS", "21"))

    # ─── PENALTY FLOORS ───
    PENALTY_FLOOR_ADVOCACY: float = float(os.getenv("PENALTY_FLOOR_ADVOCACY", "0.10"))
    PENALTY_FLOOR_AGE: float = float(os.getenv("PENALTY_FLOOR_AGE", "0.30"))
    PENALTY_FLOOR_TICKETS: float = float(os.getenv("PENALTY_FLOOR_TICKETS", "0.20"))
    PENALTY_FLOOR_GLOBAL: float = float(os.getenv("PENALTY_FLOOR_GLOBAL", "0.05"))

    # ─── ENGAGEMENT BENCHMARK ───
    BENCHMARK_ENGAGEMENT_RATE: float = float(os.getenv("BENCHMARK_ENGAGEMENT_RATE", "0.02"))


settings = Settings()
