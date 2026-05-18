# Database Mock — Documentation & Test Guide

> **Status:** Mock-only. No real PostgreSQL connection yet.
> **Source:** `src/referral_engine/tools/database_tools.py` + in-memory `_jobs` dict in `main.py`
> **Part of:** [Test Harness README](README.md)

---

## Overview

The Referral Engine's data layer has two components:

1. **Mock Database Tools** (`database_tools.py`) — 3 CrewAI `@tool` wrappers that return hardcoded data instead of querying PostgreSQL
2. **In-Memory Job Store** (`main.py:_jobs`) — A Python dict used for dev/test instead of the `jobs` / `referral_plans` tables

Both are marked as **Gap #1** and **Gap #3** in `STATUS.md` — real PostgreSQL is not yet wired.

---

## Mock Database Tools

### 1. `DatabaseQueryTool` (`database_query_tool`)

**Purpose:** Query user profile, 90-day events, social accounts, referral history from PostgreSQL.

**Used by:** Agent 1 (Signal Parser) — every analysis run, when `data` is empty in the request payload.

**Default return:**

```json
{
  "profile": {
    "id": "<user_id>",
    "created_at": "2025-01-15T00:00:00Z",
    "last_active_at": "2026-05-10T12:00:00Z",
    "account_age_days": 484
  },
  "events": [
    {"event_type": "login", "payload": {"count": 1}, "created_at": "2026-05-10T12:00:00Z"},
    {"event_type": "feature_used", "payload": {"feature": "analytics", "count": 5}, "created_at": "2026-05-09T10:00:00Z"},
    {"event_type": "support_ticket", "payload": {"status": "resolved"}, "created_at": "2026-05-01T08:00:00Z"}
  ],
  "social_accounts": {
    "platform": "twitter",
    "handle": "test_user",
    "followers": 1200,
    "following": 500,
    "tweet_count": 350,
    "engagement_rate": 0.035,
    "connected_at": "2025-06-01T00:00:00Z",
    "last_synced_at": "2026-05-10T12:00:00Z"
  },
  "prior_referrals": 3,
  "last_asked_at": "2026-04-20T10:00:00Z",
  "last_declined_at": null
}
```

| Field | Maps to | Drives |
|---|---|---|
| `profile.created_at` | `account_age_days` | PCU score |
| `profile.last_active_at` | `last_active_at` | Ask Orchestrator recency check |
| `events[]` | `raw_events` | Activity trend analysis (Agent 2) |
| `events[].event_type = "support_ticket"` | `support_tickets_90d` | Advocacy score |
| `social_accounts.followers` | `twitter_followers` | Reach score |
| `social_accounts.engagement_rate` | `twitter_engagement_rate` | Reach score |
| `prior_referrals` | `prior_referrals_total` | Ask Orchestrator gate |
| `last_asked_at` | `last_asked_at` | Cool-down gate (30-day minimum) |
| `last_declined_at` | `last_declined_at` | Re-ask delay gate |

**Production SQL it would run (3 queries):**

```sql
-- Query 1: User profile
SELECT id, created_at, last_active_at,
       EXTRACT(DAY FROM NOW() - created_at) AS account_age_days
FROM users WHERE id = $1;

-- Query 2: Events (90 days)
SELECT event_type, payload, created_at
FROM user_events WHERE user_id = $1
AND created_at >= NOW() - INTERVAL '90 days';

-- Query 3: Social accounts
SELECT platform, handle, followers, following, tweet_count,
       engagement_rate, connected_at, last_synced_at
FROM user_social_accounts WHERE user_id = $1;
```

---

### 2. `HttpReceiveTool` (`http_receive_tool`)

**Purpose:** Validate and extract user data from an HTTP push payload (the `data` field in `POST /v1/referral/analyze`). Ensures `events` is a list and `profile` is a dict.

**Used by:** Agent 1 (Signal Parser) — validates incoming `AnalyzeRequest.data`.

**Success return:**
```json
{
  "valid": true,
  "events": [...],
  "profile": {...},
  "event_count": 3
}
```

**Error return:**
```json
{"error": "Missing required key: events", "valid": false}
```

---

### 3. `DataNormalizerTool` (`data_normalizer_tool`)

**Purpose:** Present raw data to the LLM with instructions to map it to `NormalizedProfile` fields. The tool itself doesn't do the normalization — the **LLM agent** interprets the data and returns structured output.

**Used by:** Agent 1 (Signal Parser) — bridges variable-schema input to Pydantic model.

**Return:**
```json
{
  "raw_data": {...},
  "schema_hint": "",
  "instruction": "Map this raw data to the NormalizedProfile schema. Extract: account_age_days, ..."
}
```

---

## In-Memory Job Store

Located in `main.py:156`:

```python
_jobs: dict[str, ReferralState] = {}
```

This dict replaces the `jobs` and `referral_plans` PostgreSQL tables for development. Jobs are stored by `job_id` and accessible via `GET /v1/referral/results/{job_id}`.

**No persistence** — server restart clears all jobs.

**In production**, `persist_results()` would upsert into `referral_plans` and update `jobs` status.

---

## PostgreSQL Schema Reference

The full DDL is in `docs/SETUP.md`. Summary of 5 planned tables:

| Table | Purpose | Status |
|---|---|---|
| `users` | User profiles (id, created_at, last_active_at, email) | Schema defined, not populated |
| `user_events` | Activity events (jsonb payload, 90-day window) | Schema defined, not populated |
| `user_social_accounts` | Twitter OAuth tokens + social metrics | Schema defined, not populated |
| `referral_plans` | Completed analysis results (curve, milestones, rewards) | Schema defined, not populated |
| `jobs` | Job lifecycle tracking (queued → completed/held/failed) | Replaced by in-memory `_jobs` dict |

---

## Test Personas

6 user profiles cover the full pipeline. Each persona JSON file in `data/` contains a complete `AnalyzeRequest` payload.

### Persona 1: Power User (`data/power_user.json`)

| Field | Value | Why |
|---|---|---|
| `account_age_days` | 607 | Long tenure → moderate PCU bonus |
| `total_product_sessions_90d` | 95 | Very high activity |
| `feature_adoption_count` | 8 | Heavy product user |
| `support_tickets_90d` | 1 | Low friction |
| `support_tickets_resolved` | 1 | All resolved |
| `recent_activity_trend` | `"rising"` | Positive momentum |
| `twitter_followers` | 5,000 | Good reach |
| `twitter_engagement_rate` | 0.052 | Strong engagement |
| `prior_referrals_total` | 8 | Proven referrer |
| `last_asked_at` | 2026-04-20 | >30 days ago (not cooled down) |
| `last_declined_at` | null | Never declined |

**Expected:** Tier=Broadcaster, should_ask=true, high urgency

---

### Persona 2: New User (`data/new_user.json`)

| Field | Value | Why |
|---|---|---|
| `account_age_days` | 14 | Very new account |
| `total_product_sessions_90d` | 5 | Minimal activity |
| `feature_adoption_count` | 1 | Barely used product |
| `support_tickets_90d` | 0 | No support history |
| `recent_activity_trend` | `"stable"` | Not enough data |
| `twitter_followers` | 0 | No social presence |
| `twitter_engagement_rate` | 0.0 | No Twitter |
| `prior_referrals_total` | 0 | Never referred |
| `last_asked_at` | null | Never asked |

**Expected:** Tier=Whisper, should_ask=false, held

---

### Persona 3: Loyal Builder (`data/builder_user.json`)

| Field | Value | Why |
|---|---|---|
| `account_age_days` | 620 | ~1.7 year tenure |
| `total_product_sessions_90d` | 72 | High product usage |
| `feature_adoption_count` | 6 | Good adoption |
| `support_tickets_90d` | 2 / 2 resolved | All resolved -> high advocacy |
| `recent_activity_trend` | `"rising"` | Positive trend |
| `twitter_followers` | 10 | Very low reach |
| `twitter_engagement_rate` | 0.005 | Low engagement |
| `twitter_following` | 100 | High ratio (10:1) suppresses relevance |
| `prior_referrals_total` | 5 | Has referred before |
| `last_asked_at` | 2026-04-15 | >30 days ago |

**Expected:** Tier=Builder, reach=24 (low), advocacy=72 (high), should_ask=true

---

### Persona 4: Viral Amplifier (`data/amplifier_user.json`)

| Field | Value | Why |
|---|---|---|
| `account_age_days` | 906 | 2.5 year tenure |
| `total_product_sessions_90d` | 22 | Low product usage |
| `feature_adoption_count` | 3 | Low adoption |
| `support_tickets_90d` | 3 / 1 resolved | 2 open tickets → low advocacy |
| `recent_activity_trend` | `"declining"` | Use engagement, not product |
| `twitter_followers` | 15,000 | Massive reach |
| `twitter_engagement_rate` | 0.041 | Strong engagement |
| `prior_referrals_total` | 3 | Some referral history |

**Expected:** Tier=Amplifier, reach=100, advocacy=23 (low), should_ask=false (gate blocked by low advocacy + open tickets)

---

### Persona 5: Declining User (`data/declining_user.json`)

| Field | Value | Why |
|---|---|---|
| `account_age_days` | 860 | Long tenure (but irrelevant here) |
| `total_product_sessions_90d` | 4 | Very low activity |
| `support_tickets_90d` | 2 / 0 resolved | Both open -> very low advocacy |
| `recent_activity_trend` | `"declining"` | Losing interest |
| `twitter_followers` | 30 | Low reach |
| `twitter_engagement_rate` | 0.004 | Negligible engagement |
| `twitter_following` | 200 | High ratio (6.7:1) suppresses relevance |
| `prior_referrals_total` | 1 | One referral ever |
| `last_declined_at` | 2026-05-08 | Recently declined |

**Expected:** Tier=Whisper, reach=27, advocacy=2, should_ask=false (3 gates blocked)

---

### Persona 6: Mid-Tier Sharer (`data/sharer_user.json`)

| Field | Value | Why |
|---|---|---|
| `account_age_days` | 347 | ~11 months |
| `total_product_sessions_90d` | 35 | Moderate usage |
| `feature_adoption_count` | 4 | Moderate adoption |
| `support_tickets_90d` | 1 / 1 resolved | Resolved |
| `recent_activity_trend` | `"stable"` | Steady |
| `twitter_followers` | 15 | Low reach |
| `twitter_engagement_rate` | 0.008 | Low engagement |
| `twitter_following` | 120 | High ratio (8:1) suppresses relevance |
| `prior_referrals_total` | 2 | Some history |

**Expected:** Tier=Sharer, reach=31 (low), advocacy=41 (mid), should_ask=false (advocacy 41 < threshold 50)

---

## 3x3 Tier Grid

The deterministic `tier_mapper.classify_tier(reach, advocacy)` produces tiers based on:

| | Low Reach (0-33) | Mid Reach (34-66) | High Reach (67-100) |
|---|---|---|---|
| **High Advocacy (67-100)** | Builder | Nurture | Broadcaster |
| **Mid Advocacy (34-66)** | Sharer | Amplifier | Broadcaster |
| **Low Advocacy (0-33)** | Whisper | Sharer | Amplifier |

Personas mapped to grid (actual computed values from `run_demo.py`):

| Persona | Reach | Advocacy | Tier |
|---|---|---|---|
| Power User | 97 | 94 | Broadcaster |
| New User | 2 | 14 | Whisper |
| Builder | 24 | 72 | Builder |
| Amplifier | 100 | 23 | Amplifier |
| Declining | 27 | 2 | Whisper |
| Sharer | 31 | 41 | Sharer |

See [EXPECTED_OUTPUTS.md](EXPECTED_OUTPUTS.md) for the full prediction matrix including gate status.

---

## How to Test Without PostgreSQL

The mock tools return data regardless of whether PostgreSQL is running. Two paths:

### Path 1: Deterministic core tests (no API key, no server)

```powershell
cd D:\referral_engine
python src\referral_engine\tests\test_core.py
python src\referral_engine\tests\test_models.py
```

These exercise scoring, tier mapping, curve building, and guardrails — covering all deterministic logic.

### Path 2: Full persona pipeline (no API key, no server)

```powershell
cd D:\referral_engine
python tests\test-scenarios\run_demo.py
```

This runs all 6 personas through the core math and guardrails, validating expected outputs.

### Path 3: API endpoint test (needs API key + server running)

```powershell
cd D:\referral_engine
# Terminal 1
uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 3000

# Terminal 2
.\tests\test-scenarios\test_curl.ps1
```

---

## Roadmap: Real PostgreSQL

| Step | What | Status |
|---|---|---|
| 1 | Create `database.py` with asyncpg connection pool | Not implemented |
| 2 | Run `SETUP.md` DDL migrations to create tables | Not done |
| 3 | Seed test data in all 5 tables | Not done |
| 4 | Replace `DatabaseQueryTool` mock with real SQL queries | Mock only |
| 5 | Wire `persist_results()` to `referral_plans` upsert | In-memory only |
| 6 | Replace `_jobs` dict with `jobs` table | In-memory only |
| 7 | Add Alembic/Prisma migrations for schema versioning | Not started |
