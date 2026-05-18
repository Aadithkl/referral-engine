# Test Harness — Referral Engine Mock Testing

> **Location:** `tests/test-scenarios/`
> **Goal:** Demonstrate and validate the Referral Engine pipeline using mock data, without requiring an API key or PostgreSQL.

---

## Quick Start

```powershell
# 1. Navigate to project root
cd D:\referral_engine

# 2. Activate venv (if not already)
.venv\Scripts\activate

# 3. Run core deterministic tests (no API key needed)
python src\referral_engine\tests\test_core.py
python src\referral_engine\tests\test_models.py

# 4. Run persona pipeline demo (no API key needed)
python tests\test-scenarios\run_demo.py

# 5. Test with FastAPI server (needs API key in .env)
# Terminal 1: uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 3000
# Terminal 2: .\tests\test-scenarios\test_curl.ps1
```

---

## What You Can Test Without an API Key

| Layer | What | Command | Results |
|---|---|---|---|
| Core Math | Reach, Advocacy, PCU scoring | `python src\tests\test_core.py` | 16/16 pass |
| Guardrails + Models | PII detection, score validation, model serialization | `python src\tests\test_models.py` | 12/12 pass |
| Persona Demo | Full pipeline logic with 6 user types | `python tests\test-scenarios\run_demo.py` | Per-persona scores, tiers, curves |
| Tool Verification | Tools are valid CrewAI objects | See `docs/TESTING.md` Layer 2 | Manual check |
| Agent Instantiation | Agents create with correct config | See `docs/TESTING.md` Layer 3 | Manual check |

## What Needs an API Key

| Layer | What | Command |
|---|---|---|
| Full Flow (LLM) | All 4 agents execute with real LLM | `crewai run` |
| API Endpoints | POST /analyze + GET /results | Start server, run `test_curl.ps1` |
| E2E | Full pipeline + PostgreSQL + Twitter | See `docs/TESTING.md` Layer 7 |

---

## Files

| File | Purpose |
|---|---|
| `TWITTER_MOCK.md` | Twitter mock API docs — 3 tools, schemas, override guide |
| `DATABASE_MOCK.md` | Database mock docs — 3 tools, 6 personas, schema, wiring guide |
| `EXPECTED_OUTPUTS.md` | Expected tier/scores/curve per persona |
| `run_demo.py` | Deterministic pipeline runner — exercises core math against all 6 personas |
| `test_curl.ps1` | PowerShell script — curl commands to test FastAPI endpoints |
| `data/power_user.json` | Test payload: high social + high advocacy |
| `data/new_user.json` | Test payload: fresh account, no social |
| `data/builder_user.json` | Test payload: high advocacy, low reach |
| `data/amplifier_user.json` | Test payload: high reach, low advocacy |
| `data/declining_user.json` | Test payload: inactive, tickets open |
| `data/sharer_user.json` | Test payload: mid-tier everything |

---

## Persona Summary

| # | Persona | Tier | should_ask | Reach | Adv | Key trait |
|---|---|---|---|---|---|---|
| 1 | Power User | Broadcaster | true | 97 | 94 | High reach + high advocacy |
| 2 | New User | Whisper | false | 2 | 14 | No history, no social |
| 3 | Builder | Builder | true | 24 | 72 | High advocacy, tiny network |
| 4 | Amplifier | Amplifier | false | 100 | 23 | 15K followers, low product engagement |
| 5 | Declining | Whisper | false | 27 | 2 | 3 gates blocked: advocacy, tickets, declined |
| 6 | Sharer | Sharer | false | 31 | 41 | Mid advocacy, just below threshold (adv 41 < 50) |

---

## How the Pipeline Works (High-Level)

```
POST /v1/referral/analyze  (persona JSON)
         │
    Agent 1 — Signal Parser
    ┌──────────────────────────┐
    │ Reads data.profile       │
    │ Calls DatabaseQueryTool  │  (mock: returns hardcoded data)
    │ Calls TwitterProfileTool │  (mock: returns followers=1200)
    │ Calls TokenRefreshTool   │  (mock: returns "valid")
    │ Outputs NormalizedProfile│
    └──────────┬───────────────┘
               │
    Agent 2 — Score Calculator
    ┌──────────────────────────┐
    │ compute_reach()          │  followers × engagement → 0-100
    │ compute_advocacy()       │  sessions, tickets, trends → 0-100
    │ compute_pcu()            │  age + followers → referral capacity
    │ classify_tier()          │  3x3 grid → tier name
    │ Outputs ScoreOutput      │
    └──────────┬───────────────┘
               │
    Agent 3 — Ask Orchestrator
    ┌──────────────────────────┐
    │ Gate checks:             │
    │  - Account age > 30d?    │
    │  - Advocacy > threshold? │
    │  - No open tickets?      │
    │  - Cool-down passed?     │
    │  - Not recently declined?│
    │ Outputs AskDecision      │
    └──────────┬───────────────┘
               │
         should_ask?
        ┌─────┴─────┐
       YES          NO
        │            │
    Agent 4     finalize_held
    Curve        status="held"
    Designer
    ┌──────────┐
    │ Hook     │
    │ Valley   │
    │ Surge    │
    │ Plateau  │
    └──────────┘
        │
    persist + webhook
```
