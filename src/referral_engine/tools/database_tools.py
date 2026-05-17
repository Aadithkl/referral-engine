"""CrewAI @tool wrappers for database queries and HTTP payload ingestion."""

from crewai.tools import tool


@tool("DatabaseQueryTool")
def database_query_tool(user_id: str) -> dict:
    """Query user profile, events (90 days), and social accounts from PostgreSQL.

    Returns dict with keys: profile, events, social_accounts, prior_referrals,
    last_asked_at, last_declined_at.

    In production this runs 3 SQL queries. For testing, returns mock data.
    """
    return {
        "profile": {
            "id": user_id,
            "created_at": "2025-01-15T00:00:00Z",
            "last_active_at": "2026-05-10T12:00:00Z",
            "account_age_days": 484,
        },
        "events": [
            {"event_type": "login", "payload": {"count": 1}, "created_at": "2026-05-10T12:00:00Z"},
            {"event_type": "feature_used", "payload": {"feature": "analytics", "count": 5}, "created_at": "2026-05-09T10:00:00Z"},
            {"event_type": "support_ticket", "payload": {"status": "resolved"}, "created_at": "2026-05-01T08:00:00Z"},
        ],
        "social_accounts": {
            "platform": "twitter",
            "handle": "test_user",
            "followers": 1200,
            "following": 500,
            "tweet_count": 350,
            "engagement_rate": 0.035,
            "connected_at": "2025-06-01T00:00:00Z",
            "last_synced_at": "2026-05-10T12:00:00Z",
        },
        "prior_referrals": 3,
        "last_asked_at": "2026-04-20T10:00:00Z",
        "last_declined_at": None,
    }


@tool("HttpReceiveTool")
def http_receive_tool(payload: dict) -> dict:
    """Validate and extract user data from an HTTP push payload.

    Expects keys: events (list) and profile (dict).
    Returns normalized dict or error.
    """
    required = ["events", "profile"]
    for key in required:
        if key not in payload:
            return {"error": f"Missing required key: {key}", "valid": False}

    events = payload.get("events", [])
    if not isinstance(events, list):
        return {"error": "events must be a list", "valid": False}

    profile = payload.get("profile", {})
    if not isinstance(profile, dict):
        return {"error": "profile must be a dict", "valid": False}

    return {
        "valid": True,
        "events": events,
        "profile": profile,
        "event_count": len(events),
    }


@tool("DataNormalizerTool")
def data_normalizer_tool(raw_data: dict, schema_hint: str = "") -> dict:
    """Normalize variable-schema user data into a structured dict.

    The LLM interprets field names, maps JSONB payloads, and produces
    a consistent output regardless of input structure.

    Note: This tool is designed to be called by an LLM agent that will
    interpret the raw data and return a NormalizedProfile. The tool itself
    provides the raw data; the LLM does the normalization.
    """
    return {
        "raw_data": raw_data,
        "schema_hint": schema_hint,
        "instruction": (
            "Map this raw data to the NormalizedProfile schema. "
            "Extract: account_age_days, last_active_at, total_product_sessions_90d, "
            "feature_adoption_count, support_tickets_90d, support_tickets_resolved, "
            "positive_outcome_events, recent_activity_trend, twitter_handle, "
            "twitter_followers, twitter_following, twitter_tweet_count, "
            "twitter_engagement_rate, prior_referrals_total, last_asked_at, last_declined_at."
        ),
    }
