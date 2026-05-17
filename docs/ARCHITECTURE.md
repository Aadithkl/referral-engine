# Architecture

## System Overview

```
                         POST /v1/referral/analyze
                                │
                         ┌──────┴──────┐
                         │  FastAPI     │
                         │  Background  │
                         │  Tasks       │
                         └──────┬──────┘
                                │
                         ┌──────┴──────┐
                         │ ReferralFlow │
                         │  (CrewAI)    │
                         └──────┬──────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
    Agent 1                Agent 2                Agent 3
  Signal Parser        Score Calculator      Ask Orchestrator
         │                      │                      │
    [Normalize]            [Score+Tier]          [Should Ask?]
         │                      │                      │
         └──────────────────────┴───────────┬──────────┘
                                            │
                                      @router()
                                       /     \
                               should_ask    should_ask
                                =True         =False
                                  │              │
                              Agent 4         hold
                          Curve Designer        │
                                  │              │
                           [Curve+Reward]   status="held"
                                  │              │
                                  └──────┬───────┘
                                         │
                                    persist +
                                    webhook
```

## Data Flow

```
Input (HTTP or DB) → Signal Parser → ReferralState.normalized_profile
                                        ↓
                                   Score Calculator → ReferralState.{reach,advocacy,pcu,tier,zone}
                                        ↓
                                   Ask Orchestrator → ReferralState.{should_ask,urgency,reasoning}
                                        ↓
                                   @router branches:
                                   ├─ should_ask=True → Curve Designer → ReferralState.{curve,rewards,channel,tone}
                                   └─ should_ask=False → finalize_held → ReferralState.status="held"
                                        ↓
                                   persist_results() + webhook_notify()
```

## Component Map

### Layer 1: Config & State
| File | Purpose |
|------|---------|
| `.env` | 50+ tunable parameters (budgets, weights, thresholds, curve shape) |
| `config.py` | `Settings` class loads `.env` into typed attributes |
| `state.py` | `ReferralState(BaseModel)` — 25 fields tracking full pipeline state |
| `models.py` | `NormalizedProfile`, `ScoreOutput`, `AskDecision`, `CurvePlan`, API req/res |

### Layer 2: Core (Deterministic, No LLM)
| File | Key Functions |
|------|---------------|
| `core/scoring_formulas.py` | `compute_reach()`, `compute_advocacy()`, `compute_pcu()` |
| `core/tier_mapper.py` | `classify_tier()`, `get_tier_budget()` |
| `core/valley_surge.py` | `build_curve()` — 4-phase piecewise curve |
| `core/variable_reward.py` | `apply_variable_layer()`, `apply_to_curve()` |

### Layer 3: Tools (CrewAI @tool Wrappers)
| File | Tools | Wraps |
|------|-------|-------|
| `tools/calculation_tools.py` | 5 tools | `scoring_formulas` + `tier_mapper` + `valley_surge` + `variable_reward` |
| `tools/trigger_tools.py` | 3 tools | Gate/trigger logic + `.env` thresholds |
| `tools/database_tools.py` | 3 tools | DB queries + HTTP payload ingestion (mock data currently) |
| `tools/twitter_tools.py` | 3 tools | Twitter API profile/tweets/token refresh (mock data currently) |

### Layer 4: Agents (Factory Functions)
| Agent | Tools | PlanningConfig | max_execution_time | Guardrail |
|-------|-------|----------------|-------------------|-----------|
| Signal Parser | 5 tools | `reasoning_effort="low"` | 90s | `validate_no_pii` |
| Score Calculator | 3 tools | `reasoning_effort="medium"` | 120s | `validate_score_range` |
| Ask Orchestrator | 3 tools | `reasoning_effort="medium"` | 120s | `validate_ask_decision` |
| Curve Designer | 3 tools | `reasoning_effort="high"` | 180s | `validate_curve_budget` |

### Layer 5: Flow & API
| Component | Location | Purpose |
|-----------|----------|---------|
| `ReferralFlow` | `main.py` | 4-agent pipeline with `@start/@listen/@router` |
| FastAPI app | `main.py` | `POST /analyze`, `GET /results/{id}`, `GET /health` |
| `run_flow()` | `main.py` | Background task executor |
| `kickoff()` | `main.py` | CLI entrypoint for `crewai run` |

### Layer 6: Security
| File | Functions |
|------|-----------|
| `security.py` | `webhook_notify()`, `verify_webhook_signature()` |
| `guardrails.py` | `validate_no_pii()`, `validate_score_range()`, `validate_ask_decision()`, `validate_curve_budget()` |

## Agent Detail

### Agent 1: Signal Parser
- **Role:** Schema-Agnostic Data Integration Engineer
- **Purpose:** Ingest raw data from DB or HTTP, normalize to `NormalizedProfile`, fetch Twitter data, manage OAuth tokens
- **Input:** `user_id` + optional `raw_events`/`raw_profile`
- **Output:** `NormalizedProfile` (Pydantic model)
- **Tools:** DatabaseQueryTool, HttpReceiveTool, DataNormalizerTool, TwitterProfileTool, TokenRefreshTool

### Agent 2: Score Calculator
- **Role:** Behavioral Quantitative Analyst
- **Purpose:** Compute Reach, Advocacy, PCU scores; classify tier; determine optimal zone
- **Input:** Normalized profile + Twitter data from state
- **Output:** `ScoreOutput` (Pydantic model)
- **Tools:** TwitterTweetsTool (conditional), CalculationTool, TierMapperTool

### Agent 3: Ask Orchestrator
- **Role:** Conversion Timing & Gate Specialist
- **Purpose:** Evaluate ALL data to decide if user should be asked for referral now
- **Input:** ALL parsed data from Agents 1 + 2 (full context)
- **Output:** `AskDecision` (Pydantic model)
- **Tools:** TriggerEvaluatorTool, UserStateQueryTool, GateCheckerTool

### Agent 4: Curve Designer
- **Role:** Incentive Systems Architect
- **Purpose:** Design personalized Valley & Surge curve with variable rewards
- **Input:** Tier, PCU, zone, urgency, social signals
- **Output:** `CurvePlan` (Pydantic model)
- **Tools:** ValleySurgeCalculatorTool, VariableRewardTool, StrategySelectorTool

## Valley & Surge Curve

```
Reward
  │
  │  Hook ($100) ─┐
  │               │  Valley ($81 x3)        Surge (exponential)        Plateau (capped)
  │               │  ┌──┐                                         ┌──┐
  │               │  │  │                                        ┌┘  └┐
  │               │  │  │                                   ┌───┘    └───
  │               └──┘  └──┐                            ┌───┘
  │                        └────────────────────────────┘
  └────────────────────────────────────────────────────────────── Steps
     1          2      3      4      5      6      7      8      9
   (hook)    (valley)              (surge)                    (plateau)
```

## API Endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `POST` | `/v1/referral/analyze` | Enqueue analysis job | API key (not enforced) |
| `GET` | `/v1/referral/results/{job_id}` | Poll job results | API key (not enforced) |
| `GET` | `/health` | Health check | None |

See [API.md](API.md) for full contract details.

## Scaling Path

| Scale | Infrastructure |
|-------|---------------|
| 500/day (MVP) | FastAPI BackgroundTasks + PostgreSQL |
| 5K/day | Redis job queue |
| 50K/day | Celery workers + Redis |
| 500K/day | Cache Twitter profiles (6h TTL), upgrade Twitter API tier |
