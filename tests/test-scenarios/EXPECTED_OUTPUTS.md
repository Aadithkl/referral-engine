# Expected Outputs -- Per-Persona Predictions

> **Verified** against `run_demo.py` deterministic pipeline (2026-05-14).
> Based on `core/scoring_formulas.py`, `core/tier_mapper.py`, and `.env` defaults.

---

## Config Reference (.env defaults)

| Parameter | Value |
|---|---|
| MIN_ADVOCACY_FOR_ASK | 50 |
| MIN_ACCOUNT_AGE_DAYS | 14 |
| DECLINED_ASK_COOLDOWN_DAYS | 21 |
| BENCHMARK_ENGAGEMENT_RATE | 0.02 |
| REACH_LOW_MAX / REACH_MID_MAX | 33 / 66 |
| ADVOCACY_LOW_MAX / ADVOCACY_MID_MAX | 33 / 66 |

---

## Persona 1: Power User (`data/power_user.json`)

| Metric | Value | Notes |
|---|---|---|
| `reach_score` | **97** | 5000 followers x5.2% engagement, balanced network (0.24 ratio) |
| `advocacy_score` | **94** | 95 sessions, 8 features, 1 ticket (resolved), rising trend |
| `pcu` | **96** | 96 referral target, strong scores boost capacity |
| `tier` | **Broadcaster** | (high, high) -- top tier |
| `should_ask` | **true** | All 4 gates pass |
| `curve budget` | $746.35 | $100 hook + 73 steps across 4 phases |

**Gates:**
- account_age(607d): PASS
- advocacy(94 >= 50): PASS
- open_tickets(0): PASS
- declined_cooldown: PASS (never declined)

---

## Persona 2: New User (`data/new_user.json`)

| Metric | Value | Notes |
|---|---|---|
| `reach_score` | **2** | 0 followers, 0% engagement, new account (14d) |
| `advocacy_score` | **14** | 5 sessions, 1 feature, no support history |
| `pcu` | **1** | Minimum floor |
| `tier` | **Whisper** | (low, low) -- bottom tier |
| `should_ask` | **false** | Blocked by low advocacy |
| `curve` | none | Status: held |

**Gates:**
- account_age(14d >= 14): PASS (barely)
- advocacy(14 < 50): **BLOCKED**
- open_tickets(0): PASS
- declined_cooldown: PASS (never declined)

---

## Persona 3: Builder (`data/builder_user.json`)

| Metric | Value | Notes |
|---|---|---|
| `reach_score` | **24** | 10 followers x0.5% engagement, high following ratio (10:1) |
| `advocacy_score` | **72** | 72 sessions, 6 features, all tickets resolved, rising trend |
| `pcu` | **1** | Tiny social reach limits capacity despite high advocacy |
| `tier` | **Builder** | (low, high) -- high advocacy, low reach |
| `should_ask` | **true** | All 4 gates pass (advocacy drives the ask) |
| `curve budget` | $748.11 | $100 hook + 7 steps, 4 phases |

**Gates:**
- account_age(620d): PASS
- advocacy(72 >= 50): PASS
- open_tickets(0): PASS
- declined_cooldown: PASS (never declined)

> Key insight: Builder is the tier for loyal users with small networks. They get a personalized curve despite low reach because their product advocacy signals strong referral potential.

---

## Persona 4: Amplifier (`data/amplifier_user.json`)

| Metric | Value | Notes |
|---|---|---|
| `reach_score` | **100** | 15K followers x4.1% engagement, excellent network (0.03 ratio) |
| `advocacy_score` | **23** | 22 sessions, 3 features, 2/3 tickets unresolved, declining trend |
| `pcu` | **183** | Huge reach pushes capacity to 183, but gated by advocacy |
| `tier` | **Amplifier** | (high, low) -- high reach, low advocacy |
| `should_ask` | **false** | Blocked by low advocacy + open tickets |
| `curve` | none | Status: held |

**Gates:**
- account_age(906d): PASS
- advocacy(23 < 50): **BLOCKED**
- open_tickets(2 unresolved): **BLOCKED**
- declined_cooldown: PASS (never declined)

> Key insight: Even with 15K followers, the engine withholds asking if the user has poor product engagement or unresolved support tickets. This prevents asking unhappy users.

---

## Persona 5: Declining User (`data/declining_user.json`)

| Metric | Value | Notes |
|---|---|---|
| `reach_score` | **27** | 30 followers x0.4% engagement, high following ratio (6.7:1) |
| `advocacy_score` | **2** | 4 sessions, 1 feature, 0/2 tickets resolved, declining trend |
| `pcu` | **1** | Minimum floor -- no basis for referral |
| `tier` | **Whisper** | (low, low) -- bottom tier |
| `should_ask` | **false** | Blocked by 3 gates: advocacy, open tickets, recently declined |
| `curve` | none | Status: held |

**Gates:**
- account_age(860d): PASS
- advocacy(2 < 50): **BLOCKED**
- open_tickets(2 unresolved): **BLOCKED**
- declined_cooldown(15d remaining): **BLOCKED**

> Key insight: This persona exercises all 3 failure modes simultaneously -- low advocacy, unresolved tickets, and a recent decline. Strongly held.

---

## Persona 6: Sharer (`data/sharer_user.json`)

| Metric | Value | Notes |
|---|---|---|
| `reach_score` | **31** | 15 followers x0.8% engagement, high following ratio (8:1) |
| `advocacy_score` | **41** | 35 sessions, 4 features, all tickets resolved, stable trend |
| `pcu` | **1** | Low social reach limits capacity |
| `tier` | **Sharer** | (low, mid) -- mid-range advocacy, low reach |
| `should_ask` | **false** | Blocked by advocacy below threshold (41 < 50) |
| `curve` | none | Status: held |

**Gates:**
- account_age(347d): PASS
- advocacy(41 < 50): **BLOCKED**
- open_tickets(0): PASS
- declined_cooldown: PASS (never declined)

> Key insight: Sharer tier users are near-threshold. A small increase in sessions, feature adoption, or trend change to "rising" could push advocacy above 50 and trigger an ask.

---

## 3x3 Tier Grid (Actual Persona Placement)

```
          Low Reach (0-33)    Mid Reach (34-66)    High Reach (67-100)
High Adv  Builder [3]                             Broadcaster [1]
  (67+)
Mid  Adv  Sharer [6]                              Broadcaster*
  (34-66)
Low  Adv  Whisper [2, 5]                          Amplifier [4]
  (0-33)
```

*Broadcaster also covers (high, mid).

---

## Tier Budgets

| Tier | Budget | Persona | Curve Phases |
|---|---|---|---|
| Broadcaster | $2,500 | Power User | hook+valley+surge+plateau (74 steps) |
| Builder | $1,200 | Builder | hook+valley+surge+plateau (8 steps) |
| Amplifier | $3,000 | -- (held) | N/A |
| Sharer | $1,500 | -- (held) | N/A |
| Whisper | $500 | -- (held) | N/A |

---

## Input Parameters That Drive Tier Changes

To change a persona's tier, adjust these fields in the JSON:

| To go from | To | Adjust |
|---|---|---|
| Sharer -> asked | Increase advocacy | +15 sessions, +1 feature, trend=rising → adv ~60 |
| Builder -> Broadcaster | Increase reach | +10 followers, lower following ratio |
| Amplifier -> asked | Increase advocacy | +25 sessions, +2 features, resolve all tickets → adv ~52 |
| Whisper -> Sharer | Increase both | +10 followers, +15 sessions, +1 feature |
