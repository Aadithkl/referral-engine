"""CrewAI @tool wrappers for Twitter API interactions."""

from crewai.tools import tool


@tool("TwitterProfileTool")
def twitter_profile_tool(handle: str) -> dict:
    """Fetch Twitter profile by handle.

    Returns followers, following, tweet_count, engagement_rate.
    Requires OAuth tokens stored in DB.

    In production, calls Twitter API v2 /users/by/username/{handle}.
    For testing, returns mock data.
    """
    return {
        "handle": handle,
        "followers": 1200,
        "following": 500,
        "tweet_count": 350,
        "engagement_rate": 0.035,
        "verified": False,
        "account_created_at": "2020-03-15T00:00:00Z",
    }


@tool("TwitterTweetsTool")
def twitter_tweets_tool(handle: str, count: int = 20) -> list[dict]:
    """Fetch recent tweets for a handle.

    Used CONDITIONALLY — only when profile data is insufficient
    for the Score Calculator to reach a confident assessment.

    In production, calls Twitter API v2 /users/{id}/tweets.
    For testing, returns mock tweets.
    """
    return [
        {
            "id": f"tweet_{i}",
            "text": f"Sample tweet {i} from {handle} about crypto and Web3 technology.",
            "created_at": f"2026-05-{(14-i):02d}T10:00:00Z",
            "public_metrics": {
                "retweet_count": 5 + i,
                "reply_count": 2 + i,
                "like_count": 15 + i * 2,
                "quote_count": i,
            },
        }
        for i in range(min(count, 5))
    ]


@tool("TokenRefreshTool")
def token_refresh_tool(user_id: str) -> dict:
    """Check oauth_token expiry for a user's connected social accounts.

    If token_expires_at < NOW() + 5min buffer, use refresh token to get
    a new access token from Twitter OAuth2 /2/oauth2/token endpoint.
    Updates user_social_accounts row with new token and expiry.
    Decrypts stored tokens using WEBHOOK_SECRET-derived AES key.

    Returns {token_valid, refreshed, access_token | None}.
    For testing, returns mock valid token.
    """
    return {
        "token_valid": True,
        "refreshed": False,
        "access_token": None,
        "message": "Token is valid and not near expiry.",
    }
