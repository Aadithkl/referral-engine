# Testing Guide

## Test Strategy

```
Layer 0: Core math         ← 16 tests  (no deps, instant)
Layer 1: Guardrails+Models ← 12 tests  (no deps, instant)
Layer 2: Tools             ← manual    (import check, no API key needed)
Layer 3: Agents            ← manual    (instantiation check)
Layer 4: Flow (no LLM)     ← manual    (state transitions verify)
Layer 5: Flow (with LLM)   ← NEEDS API KEY
Layer 6: API               ← NEEDS API KEY + running server
Layer 7: E2E               ← NEEDS API KEY + PostgreSQL + Twitter
```

---

## Layer 0: Core Math Tests

**No dependencies. Instant. Always run first.**

```bash
cd D:\referral_engine
python src\referral_engine\tests\test_core.py
```

**Expected output:** `16/16 tests passed`

**What's tested:**
| Test | What it verifies |
|------|-----------------|
| `test_compute_reach_power_user` | 5000 followers, 0.05 engagement → high reach (80-100) |
| `test_compute_reach_zero_followers` | No social → low reach (0-30) |
| `test_compute_advocacy_rising` | Good metrics + rising trend → high advocacy (70-100) |
| `test_compute_advocacy_declining` | Poor metrics + unresolved tickets → low advocacy (0-40) |
| `test_compute_pcu_minimum` | No followers, new account → PCU = 1 minimum |
| `test_compute_pcu_with_followers` | 2000 followers, 365 days → PCU ≥ 10 |
| `test_classify_tier_broadcaster` | High reach + high advocacy = Broadcaster |
| `test_classify_tier_whisper` | Low reach + low advocacy = Whisper |
| `test_classify_tier_builder` | Low reach + high advocacy = Builder |
| `test_get_tier_budget_returns_float` | All 6 tiers have positive budgets |
| `test_build_curve_has_four_phases` | Curve has hook, valley, surge, plateau |
| `test_build_curve_hook_first` | First milestone is a hook with substantial reward |
| `test_build_curve_surge_accelerates` | Surge rewards increase monotonically |
| `test_variable_reward_reproducible` | Same seed → same reward |
| `test_variable_reward_in_range` | 10 rewards all within 75%-420% of baseline |
| `test_apply_to_curve_enriches_milestones` | Variable reward fields added to each milestone |

---

## Layer 1: Guardrails + Models Tests

**No dependencies. Instant.**

```bash
python src\referral_engine\tests\test_models.py
```

**Expected output:** `12/12 tests passed`

**What's tested:**
| Test | What it verifies |
|------|-----------------|
| `test_validate_no_pii_clean` | Clean text passes |
| `test_validate_no_pii_email_blocked` | Email address detected and blocked |
| `test_validate_score_range_valid` | Scores 0-100 pass |
| `test_validate_score_range_too_high` | Score >100 blocked |
| `test_validate_ask_decision_valid` | Valid urgency + boolean passes |
| `test_validate_ask_decision_bad_urgency` | Urgency >1.0 blocked |
| `test_validate_curve_budget_valid` | Non-negative reward + populated milestones pass |
| `test_validate_curve_budget_empty_milestones` | Empty milestones blocked |
| `test_referral_state_defaults` | All state fields have correct defaults |
| `test_analyze_request_model` | Request model serializes correctly |
| `test_analyze_response_model` | Response model serializes correctly |
| `test_settings_loads` | 50+ env vars load, TIER_BUDGETS has 6 entries |

---

## Layer 2: Tool Verification

**No API key needed. Verify tools are valid CrewAI objects.**

```bash
python -c "
import sys; sys.path.insert(0,'src')
from referral_engine.tools.calculation_tools import calculation_tool, tier_mapper_tool
from referral_engine.tools.trigger_tools import gate_checker_tool
# Verify tools are CrewAI Tool objects
assert hasattr(calculation_tool, 'name'), 'Not a CrewAI tool'
assert calculation_tool.name == 'CalculationTool'
print('CalculationTool OK')
# Test a tool run
r = tier_mapper_tool.run(reach=68, advocacy=72)
assert r['tier'] == 'Broadcaster'
print(f'TierMapper OK: {r[\"tier\"]}')
# Test gate checker
g = gate_checker_tool.run(account_age_days=180, advocacy_score=65, support_tickets_90d=3, support_tickets_resolved=3, last_declined_at='')
assert len(g['gates_passed']) == 4
print(f'GateChecker OK: {len(g[\"gates_passed\"])} gates passed')
print('All tool checks passed')
"
```

---

## Layer 3: Agent Instantiation

**No API key needed. Verify agents create correctly.**

```bash
python -c "
import sys; sys.path.insert(0,'src')
from referral_engine.agents.signal_parser import create_signal_parser
from referral_engine.agents.score_calculator import create_score_calculator
from referral_engine.agents.ask_orchestrator import create_ask_orchestrator
from referral_engine.agents.curve_designer import create_curve_designer
for create_fn in [create_signal_parser, create_score_calculator, create_ask_orchestrator, create_curve_designer]:
    agent = create_fn()
    assert agent.role, 'Missing role'
    assert agent.goal, 'Missing goal'
    assert agent.backstory, 'Missing backstory'
    assert len(agent.tools) >= 3, f'Expected >=3 tools, got {len(agent.tools)}'
    assert agent.planning_config is not None, 'Missing PlanningConfig'
    assert agent.guardrail is not None, 'Missing guardrail'
    print(f'{agent.role} OK ({len(agent.tools)} tools)')
print('All agents created successfully')
"
```

**Expected output:**
```
Schema-Agnostic Data Integration Engineer OK (5 tools)
Behavioral Quantitative Analyst OK (3 tools)
Conversion Timing & Gate Specialist OK (3 tools)
Incentive Systems Architect OK (3 tools)
All agents created successfully
```

---

## Layer 4: Flow State Transitions (Manual)

**No API key needed. Set agent result manually.**

```bash
python -c "
import sys; sys.path.insert(0,'src')
from referral_engine.main import ReferralFlow
from referral_engine.state import ReferralState

# Verify state model
state = ReferralState(user_id='test_123', status='queued')
assert state.user_id == 'test_123'
assert state.status == 'queued'

# Verify flow class exists with correct decorators
flow = ReferralFlow()
assert hasattr(flow, 'state'), 'Flow has no state'

# Check methods are decorated
import inspect
methods = [(name, str(getattr(flow, name))) for name in dir(flow) if not name.startswith('_')]
print('Flow methods:')
for name, _ in methods:
    print(f'  {name}')

# Verify router method exists
assert hasattr(flow, 'route_ask'), 'Missing route_ask (router)'
assert hasattr(flow, 'parse_signals'), 'Missing parse_signals (start)'
assert hasattr(flow, 'design_curve'), 'Missing design_curve (listen)'
assert hasattr(flow, 'finalize_held'), 'Missing finalize_held (listen hold)'
print('Flow structure verified')
"
```

---

## Layer 5: Flow with LLM

**NEEDS `OPENAI_API_KEY` set in `.env`**

```bash
# 1. Set your API key
# Edit .env: OPENAI_API_KEY=sk-your-key-here

# 2. Run CLI mode
cd D:\referral_engine
crewai run
```

**Expected:** The flow executes all 4 agents. Output shows:
1. Signal Parser normalizes data
2. Score Calculator computes scores
3. Ask Orchestrator decides should_ask
4. Curve Designer (if should_ask) builds curve
5. Final state is printed as JSON

**To test specific scenarios**, edit the `kickoff()` function in `main.py` to change inputs:
```python
flow.kickoff(inputs={
    "user_id": "test_power_user",
    "raw_events": [...],
    "raw_profile": {...},
})
```

---

## Layer 6: API Tests

**NEEDS API KEY + running server**

```bash
# Terminal 1: Start server
cd D:\referral_engine
uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Test endpoints
```

### Health check
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Submit analysis
```bash
curl -X POST http://localhost:8000/v1/referral/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "source": "product_backend",
    "data": {
      "events": [],
      "profile": {}
    },
    "callback_url": null
  }'
# → {"job_id":"job_abc123def456","status":"queued","estimated_time":"10-15s"}
```

### Poll results
```bash
curl http://localhost:8000/v1/referral/results/job_abc123def456
# → {"job_id":"job_abc123def456","status":"completed","user_id":"user_123",...}
```

---

## Layer 7: End-to-End

**NEEDS: API key + PostgreSQL + Twitter OAuth**

Full E2E test checklist:
- [ ] PostgreSQL running with schema tables
- [ ] Test user seeded in `users` table
- [ ] Test events in `user_events` table (90 days)
- [ ] Twitter OAuth configured (optional for MVP)
- [ ] `OPENAI_API_KEY` set
- [ ] Server running on port 8000
- [ ] `POST /v1/referral/analyze` returns `job_id`
- [ ] `GET /v1/referral/results/{job_id}` returns completed plan
- [ ] Webhook fires to `callback_url` (if set)
- [ ] `referral_plans` row created in DB
- [ ] `jobs` row created in DB

---

## Running All Tests Together

```bash
# No-API-key tests (always pass)
python src\referral_engine\tests\test_core.py
python src\referral_engine\tests\test_models.py

# API-key tests (need OPENAI_API_KEY)
crewai run
```

## Debugging Tips

| Symptom | Check |
|---------|-------|
| `AuthenticationError` | `OPENAI_API_KEY` set in `.env`? |
| `ModuleNotFoundError` | `pip install -e .` or `uv sync`? |
| Agent loops forever | Lower `max_iter`, check task description clarity |
| Structured output fails | Simplify Pydantic model, use simpler LLM |
| Tool not found | Tool file in `tools/` and imported in agent? |
| `@router` not branching | Return string matches `@listen("label")` exactly? |
| Guardrail blocks output | Check guardrail function logic, increase `guardrail_max_retries` |
