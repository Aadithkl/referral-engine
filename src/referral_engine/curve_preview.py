"""curve_preview.py -- Dashboard backend for ratio-based curve designer.

Four archetypes: Influencer, Broadcaster, Fan, Newcomer.
Each has 5 unitless ratio params. Global BASE_REWARD anchors all curves.
Agent assigns actual unit (dollars, credits, points) at runtime.

Penalty factor computed from gate thresholds and included in preview response.
"""

from __future__ import annotations

import os
from typing import Any

from .core.tier_mapper import classify_quadrant
from .core.valley_surge import build_curve as _build_curve, _defaults as _curve_defaults
from .core.variable_reward import apply_to_curve as _apply_to_curve
from .core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from .core.penalty import compute_penalty
from .config import settings

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

PERSONA_TEST_FIELDS = [
    {"key": "tw_followers",    "label": "Twitter followers",        "type": "int",   "default": 5000},
    {"key": "tw_engagement",   "label": "Engagement rate",          "type": "pct",  "default": 0.052},
    {"key": "tw_following",    "label": "Twitter following",        "type": "int",   "default": 1200},
    {"key": "account_age",     "label": "Account age (days)",       "type": "int",   "default": 607},
    {"key": "sessions_90d",    "label": "Sessions (90 days)",       "type": "int",   "default": 95},
    {"key": "features_adopted","label": "Features adopted",         "type": "int",   "default": 8},
    {"key": "positive_outcomes","label": "Positive outcomes",       "type": "int",   "default": 15},
    {"key": "support_tickets", "label": "Support tickets (90d)",    "type": "int",   "default": 1},
    {"key": "tickets_resolved","label": "Tickets resolved",         "type": "int",   "default": 1},
    {"key": "activity_trend",  "label": "Activity trend",           "type": "select", "options": ["rising", "stable", "declining"], "default": "rising"},
]

QUADRANT_PARAM_DEFS = [
    {"key": "HOOK_RATIO",       "label": "Hook ratio",          "type": "float",  "min": 0.1, "max": 3.0,  "step": 0.1},
    {"key": "VALLEY_DROP",      "label": "Valley drop",         "type": "pct",    "min": 0.05,"max": 0.90, "step": 0.05},
    {"key": "VALLEY_STEPS",     "label": "Valley steps",        "type": "int",    "min": 0,   "max": 10,   "step": 1},
    {"key": "PEAK_RATIO",       "label": "Peak ratio",         "type": "float",  "min": 1.0, "max": 10.0, "step": 0.1},
    {"key": "POST_CAP",         "label": "Post-target cap",     "type": "float",  "min": 1.0, "max": 5.0,  "step": 0.1},
]

QUADRANTS = ["Influencer", "Broadcaster", "Fan", "Newcomer"]

THRESHOLD_DEFS = [
    {"key": "RAW_FOLLOWERS_HIGH",    "label": "High followers min",     "type": "int",   "min": 100,  "max": 10000, "step": 100},
    {"key": "RAW_ENGAGEMENT_HIGH",   "label": "High engagement min",    "type": "pct",   "min": 0.001,"max": 0.1,   "step": 0.001},
    {"key": "RAW_SESSIONS_HIGH",     "label": "High sessions min",      "type": "int",   "min": 5,   "max": 200,   "step": 5},
    {"key": "RAW_FEATURES_HIGH",     "label": "High features min",      "type": "int",   "min": 1,   "max": 20,    "step": 1},
]


class _SettingsOverride:
    def __init__(self, **overrides):
        self._originals = {}
        for key, value in overrides.items():
            if hasattr(settings, key):
                self._originals[key] = getattr(settings, key)
                setattr(settings, key, value)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        for key, value in self._originals.items():
            setattr(settings, key, value)


def compute_test_curve(test_data: dict[str, Any], setting_overrides: dict[str, Any] | None = None) -> dict:
    """Compute curve from raw test-persona data, optionally overriding settings."""
    f = test_data.get("tw_followers", 0)
    eng = test_data.get("tw_engagement", 0.0)
    fng = test_data.get("tw_following", 0)
    age = test_data.get("account_age", 0)
    ses = test_data.get("sessions_90d", 0)
    feat = test_data.get("features_adopted", 0)
    out = test_data.get("positive_outcomes", 0)
    tix = test_data.get("support_tickets", 0)
    res = test_data.get("tickets_resolved", 0)
    trend = test_data.get("activity_trend", "stable")

    with _SettingsOverride(**(setting_overrides or {})):
        reach, _ = compute_reach(f, eng, fng, age)
        adv, _ = compute_advocacy(ses, feat, out, tix, res, trend)
        pcu, _ = compute_pcu(f, age, adv)
        quadrant = classify_quadrant(reach, adv)
        urgency = min(1.0, adv / 100.0)
        oz = [1, max(1, int(pcu * settings.OPTIMAL_ZONE_PERCENTAGE))]

        penalty, penalty_reasons = compute_penalty(age, adv, tix, res)
        penalized_base = settings.BASE_REWARD * penalty

        milestones, total_budget = _build_curve(quadrant, pcu, oz, max(urgency, 0.5), base_reward=penalized_base)
        enriched = _apply_to_curve(milestones, seed=42)

    phase_colors = {"hook": "#10b981", "valley": "#f59e0b", "surge": "#ef4444", "plateau": "#8b5cf6"}

    return {
        "scores": {"reach": reach, "advocacy": adv, "pcu": pcu},
        "quadrant": quadrant,
        "penalty_factor": penalty,
        "penalty_reasons": penalty_reasons,
        "penalized_base": round(penalized_base, 2),
        "budget": total_budget,
        "urgency": round(urgency, 2),
        "total_budget": round(total_budget, 2),
        "step_count": len(enriched),
        "milestones": [
            {
                "step": m["step"],
                "baseline": m["baseline_reward"],
                "variable": m["variable_reward"],
                "phase": m["phase"],
                "reward_type": m["reward_type"],
                "phase_color": phase_colors.get(m["phase"], "#6b7280"),
            }
            for m in enriched
        ],
    }


def get_dashboard_config() -> dict[str, Any]:
    """Return all dashboard configuration."""
    defaults = _curve_defaults()
    return {
        "base_reward": settings.BASE_REWARD,
        "test_fields": PERSONA_TEST_FIELDS,
        "quadrant_params": QUADRANT_PARAM_DEFS,
        "quadrant_values": {
            q: {
                p["key"].lower(): _get_param_value(defaults, q.upper() + "_" + p["key"])
                for p in QUADRANT_PARAM_DEFS
            }
            for q in QUADRANTS
        },
        "thresholds": [_get_threshold_value(t) for t in THRESHOLD_DEFS],
    }


def _get_threshold_value(defn: dict) -> dict:
    d = dict(defn)
    d["value"] = getattr(settings, defn["key"], defn.get("default", 0))
    return d


def _get_param_value(defaults: dict, full_key: str) -> float:
    val = getattr(settings, full_key, defaults.get(full_key, 0))
    return float(val)


def parse_overrides(params: dict[str, str]) -> dict[str, Any]:
    """Parse URL query params into typed override dict for settings."""
    overrides = {}
    tmap = {"int": int, "float": float, "dollar": float, "pct": float}
    known_keys = {"BASE_REWARD": {"type": "float"}}
    for s in QUADRANT_PARAM_DEFS:
        for q in QUADRANTS:
            known_keys[q.upper() + "_" + s["key"]] = s
    for t in THRESHOLD_DEFS:
        known_keys[t["key"]] = t

    for key, val in params.items():
        if key in known_keys:
            stype = known_keys[key].get("type", "float")
            cast = tmap.get(stype, float)
            overrides[key] = cast(val)
        else:
            try:
                overrides[key] = float(val) if "." in val or "e" in val.lower() else int(val)
            except ValueError:
                overrides[key] = val
    return overrides


def save_settings(data: dict[str, Any]) -> dict:
    """Write quadrant curve params to .env. Only updates keys that already exist."""
    if not os.path.exists(ENV_PATH):
        return {"ok": False, "error": f".env not found at {ENV_PATH}"}

    with open(ENV_PATH) as f:
        lines = f.readlines()

    updates = {k: str(int(v) if isinstance(v, float) and v == int(v) else v) for k, v in data.items() if k in _all_quadrant_keys()}

    updated_lines = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=")[0].strip()
            if key in updates:
                updated_lines.append(f"{key}={updates[key]}\n")
                del updates[key]
                continue
        updated_lines.append(line)

    with open(ENV_PATH, "w") as f:
        f.writelines(updated_lines)

    for key, value in data.items():
        if hasattr(settings, key):
            setattr(settings, key, type(getattr(settings, key))(value))
    return {"ok": True, "saved": list(data.keys())}


def _all_quadrant_keys() -> set[str]:
    keys = {"BASE_REWARD"}
    for q in QUADRANTS:
        for p in QUADRANT_PARAM_DEFS:
            keys.add(q.upper() + "_" + p["key"])
    for t in THRESHOLD_DEFS:
        keys.add(t["key"])
    return keys
