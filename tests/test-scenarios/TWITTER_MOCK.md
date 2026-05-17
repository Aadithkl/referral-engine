# Twitter API Mock — Documentation & Test Guide

> **Status:** Mock-only. No real Twitter API calls are made yet.
> **Source:** `src/referral_engine/tools/twitter_tools.py`
> **Part of:** [Test Harness README](README.md)

---

## Overview

The Referral Engine uses Twitter data to compute **Reach Score** (social influence) and enrich the **Signal Parser** (Agent 1). Since Twitter OAuth 2.0 is not yet wired (see `STATUS.md` Gap #2), **3 mock tools** provide hardcoded data for development and testing.

All 3 are registered as CrewAI `@tool` decorators — they look like real API calls to the LLM agents but return deterministic mock data.

---

## Mock Tools

### 1. `TwitterProfileTool` (`twitter_profile_tool`)

**Purpose:** Fetch a user's Twitter profile by handle.

**Used by:** Agent 1 (Signal Parser) — every analysis run.

**Default return:**

```json
{
  "handle": "<input_handle>",
  "followers": 1200,
  "following": 500,
  "tweet_count": 350,
  "engagement_rate": 0.035,
  "verified": false,
  "account_created_at": "2020-03-15T00:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `handle` | string | Echoes the input handle |
| `followers` | int | Follower count — drives `compute_reach()` |
| `following` | int | Accounts following |
| `tweet_count` | int | Total tweets posted |
| `engagement_rate` | float | (likes + retweets + replies) / followers — drives `compute_reach()` |
| `verified` | bool | Twitter verified badge |
| `account_created_at` | string | ISO 8601 timestamp |

**Production endpoint it would call:** `GET /2/users/by/username/{handle}` (Twitter API v2)

---

### 2. `TwitterTweetsTool` (`twitter_tweets_tool`)

**Purpose:** Fetch recent tweets for a handle (up to 20). Used **conditionally** — only when profile-level data is insufficient for the Score Calculator to reach a confident assessment.

**Used by:** Agent 2 (Score Calculator) — conditional invocation.

**Default return (5 tweets):**

```json
[
  {
    "id": "tweet_0",
    "text": "Sample tweet 0 from <handle> about crypto and Web3 technology.",
    "created_at": "2026-05-14T10:00:00Z",
    "public_metrics": {
      "retweet_count": 5,
      "reply_count": 2,
      "like_count": 15,
      "quote_count": 0
    }
  },
  {
    "id": "tweet_1",
    "text": "Sample tweet 1 from <handle> about crypto and Web3 technology.",
    "created_at": "2026-05-13T10:00:00Z",
    "public_metrics": {
      "retweet_count": 6,
      "reply_count": 3,
      "like_count": 17,
      "quote_count": 1
    }
  }
]
```

> Generates `min(count, 5)` tweets with incrementing metrics.

| Field | Type | Description |
|---|---|---|
| `id` | string | Tweet ID |
| `text` | string | Tweet content |
| `created_at` | string | ISO 8601 (descending days) |
| `public_metrics.retweet_count` | int | Retweets |
| `public_metrics.reply_count` | int | Replies |
| `public_metrics.like_count` | int | Likes |
| `public_metrics.quote_count` | int | Quote tweets |

**Production endpoint it would call:** `GET /2/users/{id}/tweets` (Twitter API v2)

---

### 3. `TokenRefreshTool` (`token_refresh_tool`)

**Purpose:** Check OAuth token expiry for a user's connected social account. If near expiry, refresh via Twitter OAuth 2.0 refresh endpoint.

**Used by:** Agent 1 (Signal Parser) — before fetching Twitter data.

**Default return:**

```json
{
  "token_valid": true,
  "refreshed": false,
  "access_token": null,
  "message": "Token is valid and not near expiry."
}
```

| Field | Type | Description |
|---|---|---|
| `token_valid` | bool | Whether the stored token is still valid |
| `refreshed` | bool | Whether a refresh was performed |
| `access_token` | string\|null | New access token (null if not refreshed) |
| `message` | string | Human-readable status |

**Production endpoint it would call:** `POST /2/oauth2/token` (Twitter OAuth 2.0)

---

## Data Flow: Mock → Pipeline

```
Agent 1: Signal Parser
  │
  ├── calls TokenRefreshTool(user_id)  →  "token valid" (always)
  │
  ├── calls TwitterProfileTool(handle) →  followers=1200, engagement=0.035
  │
  └── populates NormalizedProfile.{twitter_followers, twitter_engagement_rate, ...}
        │
        ▼
Agent 2: Score Calculator
  │
  ├── reads NormalizedProfile
  ├── calls compute_reach(twitter_followers=1200, twitter_engagement=0.035) → reach_score ≈ 68
  │
  └── (may call TwitterTweetsTool if needing more signal)
```

**Key insight:** With default mock data (`followers=1200`, `engagement=0.035`), the Score Calculator produces a mid-high Reach score. The actual score varies based on the LLM's internal computation + the `scoring_formulas.py` deterministic math.

---

## Test Scenarios

The default mock returns the same data regardless of input. To test **different user profiles**, the persona JSON data files in `data/` supply varying `twitter_*` fields in their `profile` objects. These feed through the `NormalizedProfile` model rather than the mock tools directly.

| Scenario | File | Followers | Engagement | Computed Reach |
|---|---|---|---|---|
| Power User | `data/power_user.json` | 5,000 | 0.052 | 97 |
| Amplifier | `data/amplifier_user.json` | 15,000 | 0.041 | 100 |
| Builder | `data/builder_user.json` | 10 | 0.005 | 24 |
| Sharer | `data/sharer_user.json` | 15 | 0.008 | 31 |
| Declining | `data/declining_user.json` | 30 | 0.004 | 27 |
| Zero Social | `data/new_user.json` | 0 | 0.0 | 2 |

---

## How to Override Mock Data

### Option A: Edit the tool file directly

Edit `src/referral_engine/tools/twitter_tools.py` and modify the hardcoded dicts:

```python
# In twitter_profile_tool():
return {
    "handle": handle,
    "followers": 5000,          # Changed from 1200
    "engagement_rate": 0.052,   # Changed from 0.035
    # ...
}
```

**Resets on git checkout** — use only for temporary testing.

### Option B: Feed data through AnalyzeRequest payload

The `POST /v1/referral/analyze` endpoint accepts a `data.profile` object. The Signal Parser (LLM agent) normalizes whatever schema you provide into `NormalizedProfile`. This is the recommended approach — use the persona JSON files in `data/`.

### Option C: Environment-variable mock

Not yet implemented. Future: add `.env` vars like `MOCK_TWITTER_FOLLOWERS=5000` to override defaults without code changes.

---

## Roadmap: Real Twitter API v2

| Step | What | Status |
|---|---|---|
| 1 | Implement `POST /auth/twitter/connect` endpoint | Not implemented |
| 2 | Implement `GET /auth/twitter/callback` (OAuth 2.0) | Not implemented |
| 3 | Store encrypted tokens in `user_social_accounts` table | Not implemented |
| 4 | Implement AES-256-GCM encryption for OAuth tokens | Not implemented |
| 5 | Wire `twitter_profile_tool` to real API v2 endpoint | Mock only |
| 6 | Wire `twitter_tweets_tool` to real API v2 endpoint | Mock only |
| 7 | Wire `token_refresh_tool` to real OAuth 2.0 refresh | Mock only |
| 8 | Upgrade Twitter API tier (Basic → Pro for 1M tweets/month) | Not started |

**Prerequisites:** Twitter Developer Account, App created in Twitter Developer Portal with OAuth 2.0 PKCE configured.
