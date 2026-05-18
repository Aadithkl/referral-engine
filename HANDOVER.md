# Referral Engine — Handover Document

**Path:** `D:\referral_engine`
**Last updated:** 2026-05-16
**Server:** `http://127.0.0.1:3000`

---

## 1. Architecture Overview

### Pipeline (4 Agentic Agents via CrewAI Flow)

```
POST /v1/referral/analyze {user_id, data: {profile: {...}}}
    ↓
┌──────────────────────────────────────────────────────────────┐
│ Agent 1: Signal Parser (LLM — DeepSeek V4 Flash)            │
│   Normalizes raw user data → NormalizedProfile               │
│   tools=[]  |  suppress_function_calling=True                │
├──────────────────────────────────────────────────────────────┤
│ Agent 2: Score Calculator (LLM + ReAct Tools)               │
│   Computes Reach, Advocacy, PCU, Tier                        │
│   tools=[calculation_tool, tier_mapper_tool]                 │
├──────────────────────────────────────────────────────────────┤
│ Agent 3: Ask Orchestrator (LLM — 3-field JSON)              │
│   Evaluates penalty factor, urgency, should_ask              │
│   tools=[]  |  3-field AskDecision model                     │
├──────────────────────────────────────────────────────────────┤
│ Agent 4: Curve Designer (LLM — varied by user data)         │
│   Designs 4-phase reward curve (hook→valley→surge→plateau)  │
│   tools=[]  |  Uses blueprint ratios as starting point      │
│   Can vary values based on user profile data                 │
└──────────────────────────────────────────────────────────────┘
    ↓
_perform_from_state() → saves curve + progress to SQLite
```

### Model & Provider

| Aspect | Value |
|--------|-------|
| **Model** | `deepseek-v4-flash` via OpenCode Go |
| **Base URL** | `https://opencode.ai/zen/go/v1` |
| **Pattern** | `LLM(model="openai/deepseek-v4-flash", base_url="https://opencode.ai/zen/go/v1")` |
| **Tool calling** | ReAct text-based (supports_function_calling=False) |
| **Agent definitions** | 4 files in `agents/`, each has `_create_llm()` with monkey-patched `supports_function_calling = lambda: False` |

---

## 2. Key Design Decisions

| # | Decision | Why |
|---|----------|-----|
| 1 | **ReAct tool calling** | opencode proxy doesn't support native `tools` API parameter. ReAct sends tools as text in prompt — works with any LLM |
| 2 | **DeepSeek V4 Flash** | 31,650 req/month on Go plan (cheapest). LiteLLM doesn't recognize `deepseek-v4-flash` → passes through to custom base_url |
| 3 | **Qwen 3.5 Plus rejected** | LiteLLM recognizes `qwen3.5-plus` as Alibaba model → ignores custom base_url → routes to Alibaba API (rate limited). Unfixable without custom LLM wrapper. |
| 4 | **Kimi K2.6 rejected** | LiteLLM doesn't recognize `kimi-k2.6` → works with custom base_url, but inconsistent: "Invalid response from LLM call - None or empty" |
| 5 | **Tools removed from Agents 3+4** | Agents couldn't complete ReAct tool calls → hit `max_iter` limit. JSON-only output (like Agent 1) proven to work |
| 6 | **Agent 2 keeps tools** | ReAct tool calling proven reliable for `calculation_tool` and `tier_mapper_tool` |
| 7 | **AskDecision simplified 7→3 fields** | 7-field model caused LLM failures. 3-field (`should_ask`, `urgency`, `reasoning`) succeeds reliably |
| 8 | **Agent 4 LLM-varying curves** | Blueprint ratios are starting point. LLM reasons about user data (followers, engagement, tickets) and varies hook/valley/surge values within reasonable bounds |
| 9 | **Penalty only for Newcomer** | Other tiers get penalty=1.0 (0% reduction). Newcomer tier gets penalty from Agent 3's calculation |
| 10 | **Deterministic fallback on every agent** | If LLM fails, Python math computes values. Pipeline always completes. `agent_status` shows "done (fallback)" |
| 11 | **Agent status tracked via `_agent_status` dict** | CrewAI Flow's `kickoff()` creates NEW pydantic state internally → `self.state.agent_status` lost. Solution: module-level `_agent_status: dict[str, list[dict]]` |
| 12 | **`_jobs` stores Flow objects, not state** | `flow.kickoff()` creates new state → `_jobs[flow]` gives dynamic `flow.state` property |

---

## 3. External Connectors

### 3.1 Referral Confirmation (Inbound)

**Endpoint:** `POST /v1/referral/confirm/{user_id}`

External referral tracker sends:
```json
{"count": 1, "timestamp": "2026-05-15T10:00:00Z"}
```

**Flow:**
1. Validates user exists in SQL (curves table)
2. Checks (user_id, timestamp) dedup in `confirmed_referrals` table
3. Looks up pre-saved curve rewards for current step
4. Updates `user_progress`: referrals_completed++, total_earned += reward
5. Pushes `RewardEvent` to registered handler (default: NoOp logger)

**No API key required** — user_id is the sole identifier from SQL data.

### 3.2 Reward Handler (Outbound)

**File:** `src/referral_engine/reward_handler.py`

```python
class RewardHandler(Protocol):
    def process(self, event: RewardEvent) -> bool: ...

class NoOpRewardHandler:
    def process(self, event: RewardEvent) -> bool:  # logs only
```

**Registration:** `reward_api.set_handler(MyHandler())`

**RewardEvent fields:** user_id, amount, unit, step, phase, referrals_completed, referrals_target, total_earned, timestamp, metadata

Future external module implements `RewardHandler` Protocol and registers via `set_handler()`.

### 3.3 Referral History

**Endpoint:** `GET /api/user/{user_id}/referrals`

Returns list of confirmed referral events from `confirmed_referrals` table with timestamps.

---

## 4. Database Schema

### SQLite at `data/referral_engine.db`

| Table | Key Fields | Purpose |
|-------|-----------|---------|
| `curves` | user_id (PK), archetype, reach_score, advocacy_score, pcu, total_budget, step_count, milestones_json, penalty_factor | Generated reward curves |
| `user_progress` | user_id (PK), referrals_completed, referrals_target, total_earned, current_step, curve_step_rewards (JSON), archetype, friendly_label, penalty_factor, reasoning, status | Live referral progress |
| `confirmed_referrals` | user_id + timestamp (PK), count | Deduplication log |

---

## 5. Frontend Views

| Route | Template | Purpose |
|-------|----------|---------|
| `/dashboard` | `templates/dashboard.html` | Backend: Curve Designer (4 blueprint charts), Test Inputs, User Tracking, Run Pipeline |
| `/overview` | `templates/overview.html` | Birds-eye: stat cards, archetype distribution, recent activity, user table |
| `/user/{user_id}` | `templates/user.html` | User-facing: credits earned, referrals count, motivational chart, recent activity. No archetype/tier/curve shown. |

### Navigation
- Dashboard header → Overview link + "View" user_id input
- Overview → Dashboard link
- User view → Dashboard + Overview links
- Run Pipeline results → "Open User View" button

---

## 6. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/referral/analyze` | Submit pipeline with user profile |
| `GET` | `/v1/referral/results/{job_id}` | Poll pipeline results (status, agent_status, scores) |
| `GET` | `/v1/referral/curves/{user_id}` | Get saved curve |
| `GET` | `/v1/referral/curves` | List curves (filter by archetype) |
| `DELETE` | `/v1/referral/curves/{user_id}` | Delete curve |
| `POST` | `/v1/referral/confirm/{user_id}` | External referral confirmation |
| `POST` | `/v1/referral/handler` | Reward handler registration (placeholder) |
| `GET` | `/api/curve/preview` | Dashboard: preview curve with test params |
| `GET` | `/api/curve/config` | Dashboard: get slider config |
| `POST` | `/api/curve/save` | Dashboard: save settings to .env |
| `GET` | `/api/curves/list` | Dashboard: list saved curves |
| `GET` | `/api/user/{user_id}/status` | User progress data |
| `GET` | `/api/user/{user_id}/referrals` | Referral confirmation history |
| `GET` | `/api/user/progress` | List all progress (filter: search, archetype, status) |
| `GET` | `/api/overview` | Aggregate stats (users, referrals, credits, archetypes) |
| `GET` | `/health` | Health check |

---

## 7. Key Files

### Backend (`src/referral_engine/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, ReferralFlow (4 agents), all endpoints |
| `config.py` | Settings from .env (BASE_REWARD, archetype ratios, thresholds) |
| `models.py` | Pydantic models: NormalizedProfile, ScoreOutput, AskDecision (3 fields), CurvePlan (with summary) |
| `state.py` | ReferralState (Flow state with agent_status field) |
| `storage.py` | SQLite persistence: curves, user_progress, confirmed_referrals |
| `reward_handler.py` | RewardHandler Protocol + RewardEvent + NoOpRewardHandler |
| `reward_api.py` | confirm_referral() + set_handler() + get_user_status() + _init_progress() |
| `curve_preview.py` | Dashboard backend: compute_test_curve(), slider config, save_settings |
| `security.py` | HMAC webhook signing |

### Agents (`src/referral_engine/agents/`)

| File | Tools | LLM Output Type |
|------|-------|----------------|
| `signal_parser.py` | [] | NormalizedProfile (JSON) |
| `score_calculator.py` | [calculation_tool, tier_mapper_tool] | ScoreOutput (JSON via ReAct) |
| `ask_orchestrator.py` | [] | AskDecision (3-field JSON) |
| `curve_designer.py` | [] | CurvePlan (with summary) |

### Core (`src/referral_engine/core/`)

| File | Purpose |
|------|---------|
| `scoring_formulas.py` | compute_reach(), compute_advocacy(), compute_pcu() |
| `tier_mapper.py` | classify_tier(), classify_quadrant(), get_tier_budget() |
| `penalty.py` | compute_penalty() — 5-factor product |
| `valley_surge.py` | build_curve() — 4-phase ratio-based curve |
| `variable_reward.py` | apply_variable_layer(), apply_to_curve() |

### Tools (`src/referral_engine/tools/`)

| File | Tools |
|------|-------|
| `calculation_tools.py` | calculation_tool, tier_mapper_tool, valley_surge_calculator_tool, variable_reward_tool, strategy_selector_tool |
| `trigger_tools.py` | trigger_evaluator_tool, gate_checker_tool |

### Templates

| File | Purpose |
|------|---------|
| `templates/dashboard.html` | 5 tabs: Curve Designer (4 blueprint charts), Test Inputs, User Tracking, Run Pipeline, Overview link |
| `templates/overview.html` | Birds-eye summary with stats, users table, recent activity |
| `templates/user.html` | Clean user-facing view: credits earned, referrals, chart, activity |

### Tests

| File | Purpose |
|------|---------|
| `tests/test_core.py` | 22 deterministic tests (scoring, penalty, curve, variable reward) |
| `tests/test_models.py` | 12 model/guardrail tests |
| `tests/test_20_users.py` | Runs 20 test personas through deterministic pipeline |
| `tests/backfill_reasoning.py` | Utility to backfill reasoning for existing users |

---

## 8. Key Fixes Applied

| # | Problem | Fix | File |
|---|---------|-----|------|
| 1 | LLM returns empty response with native tools | ReAct mode: `supports_function_calling = lambda: False` | `agents/*.py` |
| 2 | Qwen 3.5 Plus routes to Alibaba (LiteLLM intercept) | Reverted to DeepSeek V4 Flash | `agents/*.py` |
| 3 | Agent 3 fails with 7-field AskDecision | Simplified to 3 fields, gate checks computed in Python | `models.py`, `main.py` |
| 4 | Agent 4 hits max_iter with tools | Removed tools, JSON-only output | `agents/curve_designer.py` |
| 5 | `agent_status` empty in pipeline results | Track via `_agent_status` module dict instead of state field | `main.py` |
| 6 | `_jobs` dict shows stale state after kickoff | Store Flow object, read state dynamically | `main.py` |
| 7 | Reasoning not shown in tracking dashboard | Added `reasoning` to `get_user_status()` return | `reward_api.py` |
| 8 | All curves look identical (no variance) | Agent 4 prompt includes user data + "room to vary values" | `main.py` |
| 9 | Blueprint charts use fixed personas | LLM varies curve values within blueprint bounds by user data | `main.py` |
| 10 | `flow.kickoff()` blocks event loop | Run in background thread via `threading.Thread` | `main.py` |
| 11 | Curve Designer parameters unclear to users | Added tooltip popups on hover: `?` icons with descriptions for HOOK_RATIO, VALLEY_DROP, VALLEY_STEPS, PEAK_RATIO, POST_CAP, BASE_REWARD | `dashboard.html` |

---

## 9. .env Settings

```
# ─── REWARD SYSTEM ───
REWARD_TYPE=credits
BASE_REWARD=10

# ─── CURVE ARCHETYPES (ratios, unitless) ───
INFLUENCER_HOOK_RATIO=1.0    INFLUENCER_VALLEY_DROP=0.25    INFLUENCER_VALLEY_STEPS=3
INFLUENCER_PEAK_RATIO=3.0    INFLUENCER_POST_CAP=2.0
BROADCASTER_HOOK_RATIO=1.2   BROADCASTER_VALLEY_DROP=0.10   BROADCASTER_VALLEY_STEPS=4
BROADCASTER_PEAK_RATIO=2.5   BROADCASTER_POST_CAP=1.3
FAN_HOOK_RATIO=0.6           FAN_VALLEY_DROP=0.70           FAN_VALLEY_STEPS=1
FAN_PEAK_RATIO=1.5           FAN_POST_CAP=1.5
NEWCOMER_HOOK_RATIO=0.4      NEWCOMER_VALLEY_DROP=0.25      NEWCOMER_VALLEY_STEPS=3
NEWCOMER_PEAK_RATIO=2.0      NEWCOMER_POST_CAP=1.2
```

---

## 10. Known Issues & Future Work

| # | Issue | Priority |
|---|-------|----------|
| 1 | Agent 3 still hits fallback ~30% of runs (3-field model helps but not 100%) | Medium |
| 2 | Blueprint charts use fixed personas (LLM variance only in pipeline, not dashboard) | Low |
| 3 | `Qwen 3.5 Plus` can't be used due to LiteLLM routing — needs custom LLM wrapper | Low |
| 4 | No auth on confirm endpoint (user_id is sole identifier) | Medium |
| 5 | Pipeline takes 40-90s per run (4 LLM calls with ReAct retries) | Low |

---

## 11. Running the Server

```powershell
cd D:\referral_engine\src
D:\referral_engine\.venv\Scripts\python.exe -m uvicorn referral_engine.main:app --host 127.0.0.1 --port 3000
```

**Running tests:**
```powershell
D:\referral_engine\.venv\Scripts\python.exe D:\referral_engine\src\referral_engine\tests\test_core.py
D:\referral_engine\.venv\Scripts\python.exe D:\referral_engine\src\referral_engine\tests\test_models.py
```

---

## 12. TODO — Next Steps for Production Readiness

### Priority 1: Twitter Pipeline (Mock Data, Production-Ready Agentic Flow)

Set up the full production pipeline using **mock Twitter data** (no real API or OAuth needed yet). The goal is to have the entire agentic flow running as it would in production, with Agent 1 pulling data from tools instead of receiving it in the payload.

| # | Task | File | What to Do |
|---|------|------|-----------|
| **12.1** | Create mock Twitter feed generator | `tools/twitter_tools.py` or new `tools/twitter_generator.py` | Replace hardcoded mock returns with a seeded random generator that produces realistic, varied Twitter profiles per archetype (followers 50-12000, engagement 0.005-0.15, tweet counts, account age). Different profile each call. |
| **12.2** | Create mock product usage generator | `tools/database_tools.py` or new `tools/usage_generator.py` | Generate realistic usage data per archetype (sessions, features adopted, tickets, outcomes, activity trend). Different profiles per archetype with believable ranges and variance. |
| **12.3** | Re-enable tools on Agent 1 | `agents/signal_parser.py` | Change `tools=[]` → `tools=[database_query_tool, twitter_profile_tool, token_refresh_tool]`. Tools are already imported but disabled. Agent 1 should call them via ReAct pattern (proven working on Agent 2's `calculation_tool`). |
| **12.4** | Add pull-mode pipeline trigger | `main.py` | Add endpoint or query param: `POST /v1/referral/analyze?mode=pull&user_id=X`. In pull mode, Agent 1's prompt instructs it to call tools to fetch Twitter + usage data instead of receiving data in the payload body. Push mode (current) stays as-is. |
| **12.5** | Test full tool-based pipeline | Run pipeline | Verify all 4 agents complete with Agent 1 using ReAct tools to fetch mock Twitter + usage data. Check agent_status shows "done" (not fallback) for Agent 1. |
| **12.6** | Add Twitter data to tracking detail | `dashboard.html` | Show mock Twitter data (followers, engagement rate, handle) in the expandable user tracking detail row alongside curve milestones and referral history. |
| **12.7** | Add usage data to tracking detail | `dashboard.html` | Show product usage metrics (sessions, features adopted, tickets, outcomes) in the same detail row. |

### Priority 2: Hardening

| # | Task | What to Do |
|---|------|-----------|
| **12.8** | API authentication | Add API key middleware (`X-API-Key` header) on `/v1/referral/analyze` and confirm endpoints |
| **12.9** | PostgreSQL migration | Swap SQLite `storage.py` for PostgreSQL using `DATABASE_URL` from `.env`. Use `asyncpg` for async queries. |
| **12.10** | Rate limiting + job queue | Replace `threading.Thread` with a proper job queue (Redis + RQ or Celery) for pipeline execution |
| **12.11** | Twitter OAuth endpoints | Implement `GET /auth/twitter/connect` (redirect to Twitter OAuth) and `GET /auth/twitter/callback` (exchange code for tokens → store encrypted in DB) when real Twitter API keys are available |
| **12.12** | Webhook retry | Add retry logic with exponential backoff to `webhook_notify()` for failed callback deliveries |

### Reference: Previous Handover

The initial architecture and earlier session context is documented at:
- **`docs/handover/HANDOVER.md`** — May 14, 2026 (476 lines): Original hybrid LLM+deterministic architecture, Kimi K2.6 model, ratio-based curve design, 2-tab dashboard, mock tools state, known issues from earlier phase.
