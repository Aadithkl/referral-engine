# Referral Engine — Documentation

> Adaptive Push-Based Referral Intelligence Engine with Valley & Surge Reward System  
> Built with CrewAI Flows + FastAPI + PostgreSQL  
> **Date:** 2026-05-14 | **Version:** 0.1.0

---

## Quick Links

| Doc | Purpose |
|-----|---------|
| [STATUS.md](STATUS.md) | Current implementation status — what's done, what's pending, gaps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, data flow, component map, design decisions |
| [SETUP.md](SETUP.md) | Prerequisites, installation, configuration, running the server |
| [TESTING.md](TESTING.md) | Test strategy, commands, expected results, human-in-the-loop checklist |
| [API.md](API.md) | API contract, endpoints, request/response schemas, webhook format |
| [handover-referral-engine.md](../handover-referral-engine.md) | Original architecture plan (source of truth, kept at project root for reference) |

---

## Project At A Glance

```
referral_engine/
├── src/referral_engine/
│   ├── main.py              # ReferralFlow + FastAPI app
│   ├── state.py             # Pydantic ReferralState
│   ├── models.py            # API request/response + structured output models
│   ├── config.py            # .env loader (50+ tunable params)
│   ├── security.py          # HMAC webhook signing + verification
│   ├── guardrails.py        # 4 agent output validators
│   ├── agents/              # 4 agent factory functions
│   ├── tools/               # 14 CrewAI @tool wrappers
│   ├── core/                # 4 deterministic math modules
│   └── tests/               # 28 tests (all passing)
├── docs/                    # This folder
├── .env                     # Environment configuration
├── pyproject.toml           # Dependencies + CrewAI type=flow
└── uv.lock                  # Locked dependencies
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Python modules | 20 |
| Agents | 4 |
| Tools | 14 |
| Core math functions | 12 |
| API endpoints | 3 |
| Tests passing | 28/28 |
| Tunable params (.env) | 50+ |
| Target scale (MVP) | 500 users/day |
