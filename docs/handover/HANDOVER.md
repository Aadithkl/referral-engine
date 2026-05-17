# Referral Engine — Handover Document

> **Date:** 2026-05-14  
> **Status:** Production-ready core pipeline, LLM agent working, interactive dashboard running  
> **Target:** AI agent handover — everything needed to continue development  

---

## Quick Start (for the next AI agent)

```powershell
cd D:\referral_engine
.venv\Scripts\activate

# Run deterministic tests (no API key needed, 28 tests)
python src\referral_engine\tests\test_core.py
python src\referral_engine\tests\test_models.py

# Run persona pipeline demo (no API key)
python tests\test-scenarios\run_demo.py

# Start the server with dashboard
uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 8000

# Open curve designer dashboard
# → http://localhost:8000/dashboard

# API call example
curl -X POST http://localhost:8000/v1/referral/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_123","data":{"profile":{"twitter_followers":5000,"twitter_engagement_rate":0.052}}}'
curl http://localhost:8000/v1/referral/results/job_<id>
```

**API key:** `opencode-go/kimi-k2.6` via OpenCode Go at `https://opencode.ai/zen/go/v1`

---

## Project Architecture

```
referral_engine/
├── src/referral_engine/
│   ├── main.py              # FastAPI app + ReferralFlow (4-agent pipeline)
│   ├── state.py             # Pydantic ReferralState (job tracking, scores, curves)
│   ├── models.py            # NormalizedProfile, AnalyzeRequest/Response, ScoreOutput, etc.
│   ├── config.py            # All .env settings loaded as typed attributes
│   ├── curve_preview.py     # Dashboard backend — preview engine + settings I/O
│   ├── guardrails.py        # PII detection, score range, curve budget validators
│   ├── security.py          # HMAC webhook signing
│   │
│   ├── agents/              # 4 CrewAI agent factory functions
│   │   ├── signal_parser.py      # Normalizes raw data → NormalizedProfile
│   │   ├── score_calculator.py   # Runs scoring formulas (minimal, unused in flow)
│   │   ├── ask_orchestrator.py   # Gate decision reasoning (minimal)
│   │   └── curve_designer.py     # Messaging channel/tone (minimal)
│   │
│   ├── core/                # Deterministic math (no LLM)
│   │   ├── scoring_formulas.py   # compute_reach(), compute_advocacy(), compute_pcu()
│   │   ├── tier_mapper.py        # classify_quadrant() — 4-quadrant split
│   │   ├── valley_surge.py       # build_curve() — simplified 3-phase curve
│   │   └── variable_reward.py    # apply_to_curve() — jackpot/mega_win randomness
│   │
│   ├── tools/               # CrewAI @tool wrappers (14 tools, all mock data)
│   └── tests/               # 28 tests — all passing
│
├── templates/
│   └── dashboard.html       # Interactive curve designer (Chart.js, 2 tabs)
│
├── tests/
│   └── test-scenarios/      # Test harness (run_demo.py, verify_crewai.py, persona data)
│       ├── data/            # 6 persona JSON files (AnalyzeRequest payloads)
│       ├── run_demo.py      # Deterministic pipeline demo (no API key)
│       ├── verify_crewai.py # Full CrewAI + API verification
│       ├── show_curves.py   # Curve display for personas
│       ├── TWITTER_MOCK.md  # Mock Twitter API docs
│       └── DATABASE_MOCK.md # Mock DB docs
│
├── .env                     # 60+ configurable parameters
├── pyproject.toml           # Dependencies
├── uv.lock                  # Locked deps
└── docs/                    # Original architecture docs
```

---

## Pipeline Flow

```
POST /v1/referral/analyze
         │
    Agent 1 — Signal Parser (LLM: Kimi K2.6 via OpenCode Go)
    ┌──────────────────────────────────────────┐
    │ Takes raw_profile + raw_events           │
    │ LLM normalizes → NormalizedProfile JSON  │
    │ Manual parse via _extract_json()         │
    └──────────────┬───────────────────────────┘
                   │
    Agent 2 — Score Calculator (DETERMINISTIC)
    ┌──────────────────────────────────────────┐
    │ compute_reach()  → followers × eng × ratio│
    │ compute_advocacy() → sessions, tickets,   │
    │                      features, trend      │
    │ compute_pcu()    → referral capacity      │
    │ classify_quadrant() → High-High, etc      │
    └──────────────┬───────────────────────────┘
                   │
    Agent 3 — Ask Orchestrator (DETERMINISTIC)
    ┌──────────────────────────────────────────┐
    │ 5 gates from .env:                       │
    │   account_age ≥ 14d                      │
    │   advocacy ≥ 50                          │
    │   unresolved_tickets ≤ 0                 │
    │   ask_cooldown ≥ 30d                     │
    │   decline_cooldown ≥ 21d                 │
    │ All pass → should_ask=True               │
    │ Any fail → status="held"                 │
    └──────────────┬───────────────────────────┘
                   │
         should_ask?
        ┌─────┴─────┐
       YES          NO
        │            │
    Agent 4       finalize_held
    Curve          status="held"
    Designer
    (DETERMINISTIC)
    ┌──────────────────┐
    │ Simplified 3-phase│
    │ curve from        │
    │ quadrant blueprint│
    │ + variable rewards│
    └──────────────────┘
        │
    persisting results + webhook
```

---

## Key Design Decisions

### 1. Hybrid LLM + Deterministic Architecture

Only **Agent 1 (Signal Parser)** uses the LLM — it normalizes raw user data into structured JSON. The other 3 agents call pure Python math functions. This avoids tool-calling incompatibilities with thinking/reasoning models (Kimi, DeepSeek, Qwen).

**Why:** CrewAI's instructor library sends `tool_choice` when agents have tools + `response_format` (Pydantic structured output). All Go models reject this combination because their thinking mode is incompatible with forced `tool_choice`.

**Fix applied:** `main.py` now sends plain text prompts asking for JSON output, then parses with `_extract_json()` → `model_validate_json()`. Agents lost their tools — deterministic functions are called directly.

### 2. Ratio-Based 5-Phase Curve (unitless blueprint)

All parameters are pure ratios — no currency unit. The orchestrating agent
assigns the actual unit (dollars, credits, points) at runtime via `base_reward`.

```
Step 1:        hook = BASE_REWARD × HOOK_RATIO
Steps 2-3:     Ramp down from hook → valley floor (fixed 2 steps)
Steps 4..4+V:  Flat valley at valley floor (V = VALLEY_STEPS)
After valley→target: linear surge valley floor → peak
After target:  peak × min(POST_CAP, 1.0 + 0.1/step)
```

All values cascade from `base_reward` via ratios:
- `hook = base_reward × HOOK_RATIO`
- `valley_floor = hook × VALLEY_DROP`
- `peak = hook × PEAK_RATIO × urgency`

The agent determines `base_reward` per user based on campaign budget and user profile.

### 3. 4 Archetypes (replaced 6-tier system)

Old: Whisper, Sharer, Amplifier, Broadcaster, Builder, Nurture (6 tiers, 3x3 grid)  
New: **Influencer, Broadcaster, Fan, Newcomer** (4 archetypes, binary split at 50)

```
              High Advocacy (≥50)    Low Advocacy (<50)
High Reach    Influencer             Broadcaster
Low Reach     Fan                    Newcomer
```

**Curve strategy per archetype (all unitless ratios):**
| | Hook ratio | Valley drop | Valley steps | Peak ratio | Post cap | Strategy |
|---|---|---|---|---|---|---|
| **Influencer** | 1.0 | 0.25 | 3 | 3.0 | 2.0 | Med hook, moderate dip, slow surge |
| **Broadcaster** | 1.2 | 0.10 | 4 | 2.5 | 1.3 | Big hook, steep drop, slow climb |
| **Fan** | 0.6 | 0.70 | 1 | 1.5 | 1.5 | Low hook, shallow dip, fast to peak |
| **Newcomer** | 0.4 | 0.25 | 3 | 2.0 | 1.2 | Low hook, steady, slow ramp |

Agent provides `base_reward` to scale all values to actual units (dollars, credits, points).
Split thresholds are configurable: `QUADRANT_REACH_SPLIT=50`, `QUADRANT_ADVOCACY_SPLIT=50`.

### 4. OpenCode Go Endpoint

Model: `kimi-k2.6`  
Base URL: `https://opencode.ai/zen/go/v1`  
API key: `sk-1t6DdsqDQTdpWE2N0lYlInq9YyIxfn3zzAIK0ghCQEieZM792bgHs6prRPsBkuHV`  
Package: `litellm` (installed for model compatibility)  

**Note:** Kimi K2.6 works for plain LLM calls. Tool calling (function_calling_llm) fails because Go models reject `tool_choice` in thinking mode. All tool-dependent logic was moved to deterministic Python calls.

---

## Configuration (.env) — Complete Reference

### LLM Provider
```
OPENAI_API_KEY=sk-1t6DdsqDQTdpWE2N0lYlInq9YyIxfn3zzAIK0ghCQEieZM792bgHs6prRPsBkuHV
OPENAI_BASE_URL=https://opencode.ai/zen/go/v1
OPENAI_MODEL_NAME=kimi-k2.6
DATABASE_URL=postgresql://user:pass@localhost/referral_engine
```

### Curve Archetype Blueprints (5 ratios × 4 archetypes + 1 global anchor)
```
# Global anchor (agent sets per user at runtime)
BASE_REWARD=10

# Influencer: high reach + high advocacy — med hook, moderate valley, slow surge
INFLUENCER_HOOK_RATIO=1.0     INFLUENCER_VALLEY_DROP=0.25  INFLUENCER_VALLEY_STEPS=3
INFLUENCER_PEAK_RATIO=3.0     INFLUENCER_POST_CAP=2.0

# Broadcaster: high reach + low advocacy — big hook, steep valley, slow climb
BROADCASTER_HOOK_RATIO=1.2    BROADCASTER_VALLEY_DROP=0.10 BROADCASTER_VALLEY_STEPS=4
BROADCASTER_PEAK_RATIO=2.5    BROADCASTER_POST_CAP=1.3

# Fan: low reach + high advocacy — low hook, shallow valley, fast to target
FAN_HOOK_RATIO=0.6            FAN_VALLEY_DROP=0.70         FAN_VALLEY_STEPS=1
FAN_PEAK_RATIO=1.5            FAN_POST_CAP=1.5

# Newcomer: low reach + low advocacy — low hook, moderate valley, slow surge
NEWCOMER_HOOK_RATIO=0.4       NEWCOMER_VALLEY_DROP=0.25    NEWCOMER_VALLEY_STEPS=3
NEWCOMER_PEAK_RATIO=2.0       NEWCOMER_POST_CAP=1.2
```

All ratios are unitless. `hook = BASE_REWARD × HOOK_RATIO`, `valley_floor = hook × VALLEY_DROP`, `peak = hook × PEAK_RATIO`.

### Variable Rewards
```
VARIANCE_FLOOR=0.75         VARIANCE_CEILING=1.4         JACKPOT_CHANCE=0.05
JACKPOT_MULTIPLIER=3.0
```

### Scoring Weights
```
REACH_FOLLOWER_WEIGHT=0.4   REACH_ENGAGEMENT_WEIGHT=0.35  REACH_RELEVANCE_WEIGHT=0.25
ADVOCACY_USAGE_WEIGHT=0.4   ADVOCACY_TREND_WEIGHT=0.2     ADVOCACY_OUTCOME_WEIGHT=0.25
ADVOCACY_SENTIMENT_WEIGHT=0.15
```

### Gate Thresholds
```
MIN_ADVOCACY_FOR_ASK=50     MIN_ACCOUNT_AGE_DAYS=14       MAX_UNRESOLVED_TICKETS=0
ASK_COOLDOWN_DAYS=30        DECLINED_ASK_COOLDOWN_DAYS=21
SUPPORT_TICKET_WINDOW_DAYS=90
```

### Tier & Quadrant Splits
```
REACH_LOW_MAX=33            REACH_MID_MAX=66              ADVOCACY_LOW_MAX=33
ADVOCACY_MID_MAX=66         QUADRANT_REACH_SPLIT=50       QUADRANT_ADVOCACY_SPLIT=50
```

### Capacity & Engagement
```
PCU_PUBLIC_POST_CONVERSION=0.008  PCU_COMMUNITY_CONVERSION=0.035
PCU_DIRECT_MESSAGE_CONVERSION=0.25  OPTIMAL_ZONE_PERCENTAGE=0.75
BENCHMARK_ENGAGEMENT_RATE=0.02
```

---

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/v1/referral/analyze` | None (dev) | Submit user for analysis, returns job_id |
| `GET` | `/v1/referral/results/{job_id}` | None (dev) | Poll results (queued → completed/held/failed) |
| `GET` | `/health` | None | Health check |
| `GET` | `/dashboard` | None | Curve designer HTML UI |
| `GET` | `/api/curve/config` | None | Returns all dashboard config (sliders, quadrants, gates) |
| `GET` | `/api/curve/preview` | None | Returns curve JSON for given test inputs + settings |
| `POST` | `/api/curve/save` | None | Writes settings to .env file |

### Analyze Request
```json
{
  "user_id": "user_123",
  "source": "product_backend",
  "data": {
    "profile": {
      "twitter_followers": 5000,
      "twitter_engagement_rate": 0.052,
      "account_age_days": 607,
      "total_product_sessions_90d": 95,
      "feature_adoption_count": 8,
      "support_tickets_90d": 1,
      "support_tickets_resolved": 1,
      "positive_outcome_events": 15,
      "recent_activity_trend": "rising",
      "prior_referrals_total": 8
    },
    "events": []
  },
  "callback_url": null
}
```

### Results Response (completed)
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "user_id": "user_123",
  "reach_score": 97,
  "advocacy_score": 94,
  "should_ask": true,
  "urgency": 0.94,
  "error": null
}
```

### Results Response (held)
```json
{
  "job_id": "job_abc123",
  "status": "held",
  "user_id": "user_123",
  "reach_score": 2,
  "advocacy_score": 14,
  "should_ask": false,
  "urgency": 0.0,
  "error": null
}
```

---

## Dashboard (`/dashboard`)

Two tabs:

**Tab 1 — Curve Designer:** Chart + Base Reward input (unitless, anchors all curves) + 4 archetype blocks (Influencer, Broadcaster, Fan, Newcomer) with 5 ratio sliders each (hook ratio, valley drop %, valley steps, peak ratio, post cap). Computed values (hook, valley floor, peak) shown per block. Pink dashed vertical line shows target PCU. "Save to .env" persists all settings.

**Tab 2 — Test Inputs:** 10 test persona fields (followers, engagement, sessions, tickets, trend, etc.) for previewing curve behavior against any archetype. "preview only" badge — these are NOT saved to .env.

**Tech stack:** Chart.js v4.4.7 + chartjs-plugin-annotation v3.0.1 (CDN), vanilla JS, no framework.

---

## Key Functions (by file)

### `src/referral_engine/core/scoring_formulas.py`
| Function | Inputs | Output | What |
|----------|--------|--------|------|
| `compute_reach()` | followers, engagement, following, age | (score 0-100, reasoning) | Social influence score — log-scaled followers + engagement benchmark + network ratio |
| `compute_advocacy()` | sessions, features, outcomes, tickets, trend | (score 0-100, reasoning) | Product loyalty score — usage depth + sentiment + trend multiplier |
| `compute_pcu()` | followers, age_days, advocacy_score | (count, reasoning) | Personal Capacity Unit — estimated referral capacity from social + advocacy |

### `src/referral_engine/core/tier_mapper.py`
| Function | Returns | What |
|----------|---------|------|
| `classify_quadrant(reach, advocacy)` | "Influencer" / "Broadcaster" / "Fan" / "Newcomer" | Binary split at QUADRANT_REACH_SPLIT (50) + QUADRANT_ADVOCACY_SPLIT (50) |
| `classify_tier(reach, advocacy)` | (archetype, justification) | Backward-compat wrapper |

### `src/referral_engine/core/valley_surge.py`
| Function | Returns | What |
|----------|---------|------|
| `build_curve(archetype, pcu, optimal_zone, urgency, base_reward=None)` | (milestones[], total_budget) | 5-phase unitless ratio-based curve with ramp-down valley. Agent passes base_reward to assign actual unit. |
| `_defaults()` | dict of 20 default params | Fallback values for all 4 archetypes |

### `src/referral_engine/core/variable_reward.py`
| Function | Returns | What |
|----------|---------|------|
| `apply_variable_layer(baseline, seed)` | (reward, type) | Applies jackpot/mega_win/normal randomness to a single step |
| `apply_to_curve(milestones, seed)` | enriched milestones | Applies variable rewards to entire curve |

### `src/referral_engine/main.py`
| Function | What |
|----------|------|
| `_evaluate_gates(age, adv, tickets, resolved, asked, declined)` | Returns (should_ask, blocks[]) — 5 configurable gates |
| `_extract_json(raw)` | Strips markdown fences + surrounding text from LLM output |
| `ReferralFlow.parse_signals()` | Agent 1 — LLM call for normalization |
| `ReferralFlow.calculate_scores()` | Agent 2 — deterministic scoring |
| `ReferralFlow.orchestrate_ask()` | Agent 3 — deterministic gate evaluation |
| `ReferralFlow.design_curve()` | Agent 4 — deterministic curve building |
| `ReferralFlow.finalize_held()` | No-ask handler |

### `src/referral_engine/curve_preview.py`
| Function | What |
|----------|------|
| `compute_test_curve(test_data, overrides)` | Computes curve from raw test inputs with optional setting overrides |
| `get_dashboard_config()` | Returns all slider definitions + current values for dashboard |
| `parse_overrides(params)` | Converts URL query params to typed Python dict |
| `save_settings(data)` | Writes key=value pairs to .env, reloads settings object |

---

## Tools State (all mock data)

All 14 CrewAI @tool functions return hardcoded mock data. They exist as valid Tool objects but are NOT called by the main pipeline (tool calling moved to deterministic functions). See `tests/test-scenarios/TWITTER_MOCK.md` and `DATABASE_MOCK.md` for full documentation.

---

## Test Harness

Located at `tests/test-scenarios/`:
- `run_demo.py` — Exercises all 6 personas through deterministic math (no API key, instant)
- `verify_crewai.py` — Tests tools, agents, flow structure, then attempts LLM calls
- `show_curves.py` — Displays full curve milestones for personas
- `data/*.json` — 6 persona AnalyzeRequest payloads covering all 4 quadrants

---

## Known Issues & Workarounds

| Issue | Status | Workaround |
|-------|--------|------------|
| Go models reject `tool_choice` with thinking mode | Permanent (API limitation) | Tools bypassed — deterministic functions called directly |
| Free models very slow in CrewAI reasoning loops | Avoided | Removed `planning_config` from agents, use Kimi K2.6 only |
| `LiteAgentOutput.pydantic` returns wrong type with tools | CrewAI bug | Removed tools from agents, parse JSON manually |
| Infinite recursion when `@listen("design_curve")` on method named `design_curve` | Fixed | Renamed listen label to `"ask_yes"` |
| PowerShell cp1252 encoding crashes on Unicode chars in CrewAI event bus | Cosmetic | Ignored — doesn't affect functionality |

---

## Session Changes Summary

### 2026-05-14 — Ratio-based curve redesign

**Naming:** High-High→Influencer, High-Low→Broadcaster, Low-High→Fan, Low-Low→Newcomer

**Curve math:** 5-phase model with ramp-down valley (steps 2-3 drop from hook to valley floor), ratio-anchored params. See Section 2 above.

**Dashboard:** Simplified Setup to Test Inputs only (removed Gates/Scoring sliders). Added computed "Valley floor: $X / Peak: $Y" display per archetype block.

**20 new .env params:** All per-archetype with ratio-based fields. Removed old HIGH_HIGH_*, HIGH_LOW_*, etc.

### Previous session

### Files created
- `src/referral_engine/curve_preview.py` — Dashboard backend
- `templates/dashboard.html` — Interactive curve designer UI
- `tests/test-scenarios/verify_crewai.py` — Full CrewAI integration test
- `tests/test-scenarios/show_curves.py` — Curve display utility
- `tests/test-scenarios/run_demo.py` — Deterministic pipeline demo
- `tests/test-scenarios/TWITTER_MOCK.md` + `DATABASE_MOCK.md` + `README.md` + `EXPECTED_OUTPUTS.md`
- `tests/test-scenarios/data/*.json` — 6 persona test files
- `tests/test-scenarios/test_curl.ps1` — PowerShell curl test script

### Files modified
- `main.py` — Hybrid LLM+deterministic pipeline, removed `response_format`, added manual JSON parsing, 5-gate system, dashboard routes, quadrant system
- `config.py` — Added 20 quadrant curve params, 2 quadrant split thresholds, 2 gate variables, removed old tier+curve params
- `tier_mapper.py` — `classify_quadrant()` replaces multi-tier grid, removed budget lookup
- `valley_surge.py` — Complete rewrite: simplified 3-phase linear curve with per-quadrant blueprints
- `curve_preview.py` — (recreated) dashboard preview engine with quadrant sliders
- `.env` — Replaced 6 tier budgets + old curve params with 20 quadrant curve params + 2 new gate vars
- `agents/signal_parser.py` — LLM=Kimi K2.6, no tools, no planning_config, reasoning=False
- `agents/score_calculator.py` — Same pattern
- `agents/ask_orchestrator.py` — Same pattern
- `agents/curve_designer.py` — Same pattern
- `templates/dashboard.html` — (rewritten multiple times) tabbed layout, 4-quadrant blocks, target line

### Dependencies added
- `litellm` — for CrewAI model compatibility with non-native providers

---

## Where to Go Next

1. **Add real PostgreSQL storage** — Replace `_jobs` dict with `asyncpg` queries. DDL exists in `docs/SETUP.md`.
2. **Add Twitter OAuth** — Implement `/auth/twitter/connect` + `/auth/twitter/callback` endpoints.
3. **Add API key validation** — Middleware for `X-API-Key` header on the analysis endpoints.
4. **Add Redis queue** — Replace FastAPI BackgroundTasks for >5K users/day throughput.
5. **Add multi-curve comparison view** — Overlay all 4 quadrant curves on the dashboard for side-by-side comparison.
6. **Add AI-driven curve optimization** — Auto-tune quadrant blueprints based on conversion rate data.
7. **Containerize** — Add Dockerfile + docker-compose for PostgreSQL + Redis + app.
