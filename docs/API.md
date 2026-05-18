# API Contract

> Base URL: `http://localhost:3000`

---

## POST /v1/referral/analyze

Enqueue a referral analysis job. Returns `job_id` immediately; processing happens async.

### Request

```http
POST /v1/referral/analyze
Content-Type: application/json
X-API-Key: your-api-key
```

```json
{
  "user_id": "user_123",
  "source": "product_backend",
  "data": {
    "events": [
      {
        "event_type": "login",
        "payload": {"count": 1},
        "created_at": "2026-05-10T12:00:00Z"
      }
    ],
    "profile": {
      "name": "Test User",
      "created_at": "2025-01-15T00:00:00Z",
      "last_active_at": "2026-05-10T12:00:00Z"
    }
  },
  "callback_url": "https://your-app.com/webhooks/referral"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | Unique user identifier |
| `source` | string | No | Origin of the request (default: `product_backend`) |
| `data.events` | array | No | User activity events (any schema — LLM normalizes) |
| `data.profile` | object | No | User profile data (any schema — LLM normalizes) |
| `callback_url` | string | No | URL to POST results to when job completes |

> **Note:** If `data` is empty or not provided, the Signal Parser queries PostgreSQL for the user's data instead.

### Response (202 Accepted)

```json
{
  "job_id": "job_abc123def456",
  "status": "queued",
  "estimated_time": "10-15s"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier for polling |
| `status` | string | Always `queued` on response |
| `estimated_time` | string | Expected processing time |

### Possible Errors

| Status | Body | Cause |
|--------|------|-------|
| 422 | Validation error | Missing required `user_id` |
| 500 | Internal error | Agent failure during processing |

---

## GET /v1/referral/results/{job_id}

Poll for job results. Job progresses through: `queued` → `completed` | `held` | `failed`.

### Request

```http
GET /v1/referral/results/job_abc123def456
X-API-Key: your-api-key
```

### Response (200 — Job Complete)

```json
{
  "job_id": "job_abc123def456",
  "status": "completed",
  "user_id": "user_123",
  "reach_score": 68,
  "advocacy_score": 72,
  "tier": "Broadcaster",
  "should_ask": true,
  "urgency": 0.85,
  "error": null
}
```

### Response (200 — Job Held)

```json
{
  "job_id": "job_abc123def456",
  "status": "held",
  "user_id": "user_123",
  "reach_score": 55,
  "advocacy_score": 38,
  "tier": "Sharer",
  "should_ask": false,
  "urgency": 0.0,
  "error": null
}
```

### Response (200 — Job Failed)

```json
{
  "job_id": "job_abc123def456",
  "status": "failed",
  "user_id": "user_123",
  "error": "Signal Parser: validation error in NormalizedProfile"
}
```

### Possible Errors

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"detail":"Job not found"}` | Invalid or expired `job_id` |

---

## GET /health

Health check — no auth required.

### Response

```json
{"status": "ok"}
```

---

## Webhook Callback

When a `callback_url` is provided in the analysis request, the engine POSTs results to that URL upon completion.

### Request (from engine → your server)

```http
POST https://your-app.com/webhooks/referral
Content-Type: application/json
X-Signature: hmac-sha256=<hex-encoded-hmac>
```

```json
{
  "user_id": "user_123",
  "job_id": "job_abc123def456",
  "status": "completed",
  "reach_score": 68,
  "advocacy_score": 72,
  "pcu": 15,
  "tier": "Broadcaster",
  "optimal_zone": [8, 15],
  "should_ask": true,
  "urgency": 0.85,
  "trigger_detail": "High advocacy + rising activity + all tickets resolved...",
  "hook_reward": 100.0,
  "milestones": [
    {
      "step": 1,
      "baseline_reward": 100.0,
      "phase": "hook",
      "description": "Step 1: First referral — instant validation reward"
    }
  ],
  "total_projected_reward": 1315.20,
  "messaging_channel": "push",
  "messaging_tone": "urgent",
  "error": ""
}
```

### Verifying Signatures

```python
import hmac, hashlib

def verify(payload: str, signature_header: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    received = signature_header.replace("hmac-sha256=", "")
    return hmac.compare_digest(expected, received)
```

---

## Job Lifecycle

```
POST /analyze → job status = "queued"
                     │
              Background task starts
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    "completed"   "held"       "failed"
   (all agents   (should_ask   (exception
    ran, curve    =False)       in agent)
    designed)
```

## Full Result State

For a completed job, the full `ReferralState` includes:

```json
{
  "user_id": "user_123",
  "job_id": "job_abc123def456",
  "status": "completed",
  "error": "",
  "reach_score": 68,
  "advocacy_score": 72,
  "pcu": 15,
  "tier": "Broadcaster",
  "optimal_zone": [8, 15],
  "should_ask": true,
  "urgency": 0.85,
  "trigger_detail": "User shows high advocacy, all tickets resolved, rising activity",
  "hook_reward": 100.0,
  "milestones": [...],
  "total_projected_reward": 1315.20,
  "messaging_channel": "push",
  "messaging_tone": "urgent",
  "twitter_followers": 1200,
  "twitter_engagement": 0.035,
  "account_age_days": 484,
  "last_active_at": "2026-05-10T12:00:00Z",
  "prior_referrals": 3,
  "last_asked_at": "2026-04-20T10:00:00Z",
  "last_declined_at": null,
  "normalized_profile": {...}
}
```

---

## Future Endpoints (Not Yet Implemented)

### POST /auth/twitter/connect
Generate Twitter OAuth 2.0 authorization URL for a user.

### GET /auth/twitter/callback
Handle OAuth 2.0 callback, exchange code for tokens, encrypt and store.

### GET /auth/twitter/status?user_id={id}
Check if a user has connected Twitter and token validity.

### POST /v1/referral/outcome
Receive referral outcome events from external system (with HMAC signature verification).
