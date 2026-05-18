"""main.py -- ReferralFlow + FastAPI application.

Orchestrates 4 LLM-powered agents via CrewAI Flow with @start/@listen decorators.
All agents are agentic — they reason with LLMs and can call deterministic tools.
No blocking gates — penalty factor scales rewards for low-metric users.
"""

import json
import os
import re
import uuid
import asyncio
import threading
import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from crewai.flow.flow import Flow, start, listen

from .state import ReferralState
from .models import NormalizedProfile, AnalyzeRequest, AnalyzeResponse
from .models import ScoreOutput, AskDecision, CurvePlan
from .agents.signal_parser import create_signal_parser
from .agents.score_calculator import create_score_calculator
from .agents.ask_orchestrator import create_ask_orchestrator
from .agents.curve_designer import create_curve_designer
from .security import webhook_notify

from .config import settings
from . import curve_preview
from .core.scoring_formulas import compute_reach, compute_advocacy, compute_pcu
from .core.tier_mapper import classify_tier
from .core.penalty import compute_penalty
from .core.valley_surge import build_curve
from .core.variable_reward import apply_to_curve
from . import storage
from . import reward_api
from .reward_handler import RewardHandler


def _extract_json(raw: str) -> str:
    """Extract a JSON object from LLM output."""
    cleaned = raw.strip()
    for fence in ("```json", "```"):
        if fence in cleaned:
            start = cleaned.find(fence) + len(fence)
            end = cleaned.rfind("```")
            if end > start:
                cleaned = cleaned[start:end].strip()
            break
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]
    return cleaned.strip()


class ReferralFlow(Flow[ReferralState]):
    """4-agent penalty-based referral analysis pipeline."""

    @start()
    def parse_signals(self):
        """Agent 1: Normalize raw data into structured profile using LLM."""
        _track_agent(self.state.job_id, "Signal Parser", "running")
        try:
            agent = create_signal_parser()
            result = agent.kickoff(
                messages=(
                    f"Normalize this user data into a structured profile.\n\n"
                    f"user_id: {self.state.user_id}\n"
                    f"raw_events: {self.state.raw_events}\n"
                    f"raw_profile: {self.state.raw_profile}\n\n"
                    "Return ONLY a JSON object with these fields (use 0 for missing numbers):\n"
                    '{\n'
                    '  "account_age_days": int,\n'
                    '  "last_active_at": string or null,\n'
                    '  "total_product_sessions_90d": int,\n'
                    '  "feature_adoption_count": int,\n'
                    '  "support_tickets_90d": int,\n'
                    '  "support_tickets_resolved": int,\n'
                    '  "positive_outcome_events": int,\n'
                    '  "recent_activity_trend": "stable" | "rising" | "declining",\n'
                    '  "twitter_followers": int,\n'
                    '  "twitter_following": int,\n'
                    '  "twitter_engagement_rate": float,\n'
                    '  "prior_referrals_total": int,\n'
                    '  "last_asked_at": string or null,\n'
                    '  "last_declined_at": string or null\n'
                    '}\n'
                    "No markdown fences, no explanation."
                ),
            )
            raw = _extract_json(result.raw)
            profile = NormalizedProfile.model_validate_json(raw)
            self.state.normalized_profile = profile.model_dump()
            self.state.twitter_followers = profile.twitter_followers or 0
            self.state.twitter_engagement = profile.twitter_engagement_rate or 0.0
            self.state.account_age_days = profile.account_age_days
            self.state.last_active_at = profile.last_active_at or ""
            self.state.prior_referrals = profile.prior_referrals_total
            self.state.last_asked_at = profile.last_asked_at or ""
            self.state.last_declined_at = profile.last_declined_at or ""
            _track_agent(self.state.job_id, "Signal Parser", "done")
        except Exception as e:
            self.state.status = "failed"
            self.state.error = f"Signal Parser: {e}"
            raise

    @listen(parse_signals)
    def calculate_scores(self):
        """Agent 2: LLM-powered score calculator with deterministic fallback."""
        _track_agent(self.state.job_id, "Score Calculator", "running")
        try:
            agent = create_score_calculator()
            p = self.state.normalized_profile

            prompt = (
                f"Compute Reach, Advocacy, PCU, and Archetype Tier for this user.\n\n"
                f"User Profile:\n"
                f"- Twitter followers: {self.state.twitter_followers}\n"
                f"- Twitter engagement rate: {self.state.twitter_engagement}\n"
                f"- Twitter following: {p.get('twitter_following', 0)}\n"
                f"- Account age: {self.state.account_age_days} days\n"
                f"- Product sessions (90d): {p.get('total_product_sessions_90d', 0)}\n"
                f"- Features adopted: {p.get('feature_adoption_count', 0)}\n"
                f"- Positive outcomes: {p.get('positive_outcome_events', 0)}\n"
                f"- Support tickets (90d): {p.get('support_tickets_90d', 0)}\n"
                f"- Tickets resolved: {p.get('support_tickets_resolved', 0)}\n"
                f"- Activity trend: {p.get('recent_activity_trend', 'stable')}\n\n"
                f"Archetype thresholds: reach split={settings.QUADRANT_REACH_SPLIT}, "
                f"advocacy split={settings.QUADRANT_ADVOCACY_SPLIT}\n"
                f"Return ONLY a JSON object:\n"
                f'{{"reach_score": int, "advocacy_score": int, "pcu": int, "tier": str, '
                f'"optimal_zone": [int, int], "reasoning": str}}\n'
                f"No markdown fences, no explanation."
            )

            result = agent.kickoff(messages=prompt)
            if not result.raw or not result.raw.strip():
                raise ValueError("LLM returned empty response")
            raw = _extract_json(result.raw)
            s = ScoreOutput.model_validate_json(raw)

            self.state.reach_score = s.reach_score
            self.state.advocacy_score = s.advocacy_score
            self.state.pcu = s.pcu
            self.state.tier = s.tier
            self.state.optimal_zone = (list(s.optimal_zone)
                                       if s.optimal_zone and len(s.optimal_zone) == 2
                                       else [1, max(1, int(s.pcu * settings.OPTIMAL_ZONE_PERCENTAGE))])
            _track_agent(self.state.job_id, "Score Calculator", "done")
        except Exception:
            p = self.state.normalized_profile
            reach, _ = compute_reach(self.state.twitter_followers, self.state.twitter_engagement,
                p.get("twitter_following", 0), self.state.account_age_days)
            advocacy, _ = compute_advocacy(p.get("total_product_sessions_90d", 0),
                p.get("feature_adoption_count", 0), p.get("positive_outcome_events", 0),
                p.get("support_tickets_90d", 0), p.get("support_tickets_resolved", 0),
                p.get("recent_activity_trend", "stable"))
            pcu, _ = compute_pcu(self.state.twitter_followers, self.state.account_age_days, advocacy)
            tier, _ = classify_tier(reach, advocacy)
            self.state.reach_score = reach
            self.state.advocacy_score = advocacy
            self.state.pcu = pcu
            self.state.tier = tier
            self.state.optimal_zone = [1, max(1, int(pcu * settings.OPTIMAL_ZONE_PERCENTAGE))]
            _track_agent(self.state.job_id, "Score Calculator", "done (fallback)")

    @listen(calculate_scores)
    def calculate_penalty(self):
        """Agent 3: LLM-powered gate evaluation with deterministic fallback."""
        _track_agent(self.state.job_id, "Ask Orchestrator", "running")
        try:
            agent = create_ask_orchestrator()
            p = self.state.normalized_profile
            tickets = p.get("support_tickets_90d", 0)
            resolved = p.get("support_tickets_resolved", 0)

            prompt = (
                f"Evaluate referral readiness. Compute penalty factor (0.05-1.0).\n"
                f"Advocacy={self.state.advocacy_score} Age={self.state.account_age_days}d "
                f"Tickets={tickets}/{resolved} Asked={self.state.last_asked_at or 'never'} "
                f"Declined={self.state.last_declined_at or 'never'}\n"
                f"Only Newcomer tier gets penalty. Other tiers=1.0.\n"
                f"Return ONLY: {{\"should_ask\": bool, \"urgency\": float, \"reasoning\": str}}\n"
                f"No fences."
            )

            result = agent.kickoff(messages=prompt)
            if not result.raw or not result.raw.strip():
                raise ValueError("LLM returned empty response")
            raw = _extract_json(result.raw)
            d = AskDecision.model_validate_json(raw)

            urgency = max(0.0, min(1.0, float(d.urgency)))
            p_factor = max(settings.PENALTY_FLOOR_GLOBAL, min(1.0, urgency))
            if self.state.tier != "Newcomer":
                p_factor = 1.0
            self.state.penalty_factor = p_factor
            self.state.urgency = urgency
            self.state.trigger_detail = d.reasoning or ""
            self.state.should_ask = d.should_ask
            _track_agent(self.state.job_id, "Ask Orchestrator", "done")
        except Exception:
            p = self.state.normalized_profile
            penalty, reasons = compute_penalty(self.state.account_age_days, self.state.advocacy_score,
                p.get("support_tickets_90d", 0), p.get("support_tickets_resolved", 0),
                self.state.last_asked_at or None, self.state.last_declined_at or None)
            if self.state.tier != "Newcomer":
                penalty = 1.0
            urgency = min(1.0, self.state.advocacy_score / 100.0)
            self.state.penalty_factor = penalty
            self.state.urgency = urgency
            self.state.trigger_detail = "; ".join(reasons)
            self.state.should_ask = True
            _track_agent(self.state.job_id, "Ask Orchestrator", "done (fallback)")

    @listen(calculate_penalty)
    def design_curve(self):
        """Agent 4: LLM-powered curve designer with deterministic fallback."""
        _track_agent(self.state.job_id, "Curve Designer", "running")
        try:
            agent = create_curve_designer()
            penalized_base = settings.BASE_REWARD * self.state.penalty_factor

            prompt = (
                f"Design reward curve.\n"
                f"User: Followers={self.state.twitter_followers} Engage={self.state.twitter_engagement:.4f} "
                f"Age={self.state.account_age_days}d Sessions={self.state.normalized_profile.get('total_product_sessions_90d',0)} "
                f"Features={self.state.normalized_profile.get('feature_adoption_count',0)} "
                f"Tickets={self.state.normalized_profile.get('support_tickets_90d',0)}\n"
                f"Tier={self.state.tier} PCU={self.state.pcu} "
                f"Urgency={self.state.urgency:.2f} Base={penalized_base:.2f}\n"
                f"Blueprint: Hook={getattr(settings, f'{self.state.tier.upper()}_HOOK_RATIO', 1.0)}x "
                f"Drop={getattr(settings, f'{self.state.tier.upper()}_VALLEY_DROP', 0.25)} "
                f"VSteps={getattr(settings, f'{self.state.tier.upper()}_VALLEY_STEPS', 3)} "
                f"Peak={getattr(settings, f'{self.state.tier.upper()}_PEAK_RATIO', 2.0)}x "
                f"Cap={getattr(settings, f'{self.state.tier.upper()}_POST_CAP', 1.5)}x\n"
                f"Use blueprint as starting point. You have room to vary exact values "
                f"based on user data without massively changing the curve shape. "
                f"Reason about all values.\n"
                f"4 phases: hook→valley→surge→plateau.\n"
                f"summary: ~100 words explaining design choices for this user.\n"
                f"Return ONLY: {{\"hook_reward\": float, \"milestones\": [{{\"step\": int, \"baseline_reward\": float, \"phase\": str, \"reward_type\": str}}], \"total_reward\": float, \"channel\": str, \"tone\": str, \"strategy_note\": str, \"summary\": str}}\n"
                f"No fences."
            )

            result = agent.kickoff(messages=prompt)
            if not result.raw or not result.raw.strip():
                raise ValueError("LLM returned empty response")
            raw = _extract_json(result.raw)
            c = CurvePlan.model_validate_json(raw)

            self.state.hook_reward = c.hook_reward
            self.state.milestones = c.milestones
            self.state.total_projected_reward = c.total_reward
            self.state.messaging_channel = c.channel
            self.state.messaging_tone = c.tone
            self.state.status = "completed"
            self.state.trigger_detail = c.summary or ""
            _track_agent(self.state.job_id, "Curve Designer", "done")
        except Exception:
            penalized_base = settings.BASE_REWARD * self.state.penalty_factor
            milestones, total_budget = build_curve(self.state.tier, self.state.pcu,
                self.state.optimal_zone, max(self.state.urgency, 0.5), base_reward=penalized_base)
            enriched = apply_to_curve(milestones, seed=42)
            channel = "push" if self.state.urgency > 0.7 else "in-app" if self.state.urgency > 0.3 else "email"
            tone = "urgent" if self.state.urgency > 0.8 else "opportunity" if self.state.urgency > 0.5 else "gentle_nudge"
            self.state.hook_reward = enriched[0]["baseline_reward"] if enriched else 0
            self.state.milestones = enriched
            self.state.total_projected_reward = total_budget
            self.state.messaging_channel = channel
            self.state.messaging_tone = tone
            self.state.status = "completed"
            self.state.trigger_detail = f"Tier={self.state.tier} PCU={self.state.pcu} Urgency={self.state.urgency:.2f} Penalty={((1-self.state.penalty_factor)*100):.0f}% (deterministic)"
            _track_agent(self.state.job_id, "Curve Designer", "done (fallback)")


# -- FastAPI app --

app = FastAPI(title="Referral Engine", version="0.1.0")
_jobs: dict[str, ReferralFlow] = {}
_agent_status: dict[str, list[dict]] = {}


def _track_agent(job_id: str, agent: str, status: str):
    if job_id not in _agent_status:
        _agent_status[job_id] = []
    _agent_status[job_id].append({"agent": agent, "status": status})


@app.post("/v1/referral/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    flow = ReferralFlow()
    flow.state.user_id = request.user_id
    flow.state.raw_events = request.data.get("events", [])
    flow.state.raw_profile = request.data.get("profile", {})
    flow.state.job_id = f"job_{uuid.uuid4().hex[:12]}"
    flow.state.status = "queued"
    _jobs[flow.state.job_id] = flow
    threading.Thread(target=_run_flow_sync, args=(flow, request.callback_url), daemon=True).start()
    return AnalyzeResponse(job_id=flow.state.job_id, status="queued", estimated_time="10-15s")


@app.get("/v1/referral/results/{job_id}", response_model=dict)
async def get_results(job_id: str):
    flow = _jobs.get(job_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="Job not found")
    state = flow.state
    return {
        "job_id": state.job_id, "status": state.status, "user_id": state.user_id,
        "reach_score": state.reach_score, "advocacy_score": state.advocacy_score,
        "penalty_factor": state.penalty_factor, "urgency": state.urgency,
        "error": state.error,
        "agent_status": _agent_status.get(job_id, []),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# -- Landing page routes --

_LANDING_DIR = os.environ.get("LANDING_PAGE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static"))


@app.get("/", response_class=HTMLResponse)
async def landing():
    path = os.path.join(_LANDING_DIR, "index.html")
    if not os.path.exists(path):
        raise HTTPException(404, "Landing page not found")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/style.css", response_class=FileResponse)
async def landing_css():
    path = os.path.join(_LANDING_DIR, "style.css")
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="text/css")


@app.get("/main.js", response_class=FileResponse)
async def landing_js():
    path = os.path.join(_LANDING_DIR, "main.js")
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="application/javascript")


@app.get("/assets/{filename}")
async def landing_assets(filename: str):
    # Prevent path traversal
    safe = os.path.basename(filename)
    path = os.path.join(_LANDING_DIR, "assets", safe)
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path)


# -- Dashboard routes --

_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "dashboard.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    if not os.path.exists(_TEMPLATE_PATH):
        raise HTTPException(404, "Dashboard template not found")
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/curve/preview")
async def curve_preview_endpoint(request: Request):
    try:
        params = dict(request.query_params)
        test_params = {
            "tw_followers": int(params.pop("tw_followers", "0") or 0),
            "tw_engagement": float(params.pop("tw_engagement", "0") or 0),
            "tw_following": int(params.pop("tw_following", "0") or 0),
            "account_age": int(params.pop("account_age", "0") or 0),
            "sessions_90d": int(params.pop("sessions_90d", "0") or 0),
            "features_adopted": int(params.pop("features_adopted", "0") or 0),
            "positive_outcomes": int(params.pop("positive_outcomes", "0") or 0),
            "support_tickets": int(params.pop("support_tickets", "0") or 0),
            "tickets_resolved": int(params.pop("tickets_resolved", "0") or 0),
            "activity_trend": params.pop("activity_trend", "stable"),
        }
        overrides = curve_preview.parse_overrides(params)
        result = curve_preview.compute_test_curve(test_params, overrides)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/curve/config")
async def curve_config():
    return curve_preview.get_dashboard_config()


@app.post("/api/curve/save")
async def curve_save(data: dict):
    try:
        parsed = curve_preview.parse_overrides(data)
        return curve_preview.save_settings(parsed)
    except Exception as e:
        raise HTTPException(400, str(e))


# -- Curve persistence endpoints --

@app.get("/v1/referral/curves/{user_id}")
async def get_curve(user_id: str):
    curve = await storage.load_curve(user_id)
    if curve is None:
        raise HTTPException(404, f"No saved curve for user '{user_id}'")
    return curve


@app.get("/v1/referral/curves")
async def list_curves_endpoint(archetype: str = None):
    return await storage.list_curves(archetype)


@app.get("/api/curves/list")
async def curves_dashboard_list():
    curves = await storage.list_curves()
    stats = await storage.get_stats()
    return {"curves": curves, "stats": stats}


@app.delete("/v1/referral/curves/{user_id}")
async def delete_curve(user_id: str):
    deleted = await storage.delete_curve(user_id)
    if not deleted:
        raise HTTPException(404, f"No saved curve for user '{user_id}'")
    return {"ok": True, "deleted": user_id}


# -- Referral confirmation endpoint (inbound from external tracker) --

@app.post("/v1/referral/confirm/{user_id}")
async def confirm_referral(user_id: str, request: Request):
    """External referral tracker confirms a referral. user_id is the unique identifier from SQL data."""
    curve = await storage.load_curve(user_id)
    if curve is None:
        raise HTTPException(404, f"No saved curve for user '{user_id}'")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    count = body.get("count", 1)
    timestamp = body.get("timestamp", "")

    if not timestamp:
        raise HTTPException(400, "timestamp field required for deduplication")

    try:
        result = await reward_api.confirm_referral(user_id, count=int(count), timestamp=timestamp)
    except ValueError as e:
        raise HTTPException(409, str(e))

    return result


# -- User-facing routes --

_USER_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "user.html")


@app.get("/user/{user_id}", response_class=HTMLResponse)
async def user_view(user_id: str):
    if not os.path.exists(_USER_TEMPLATE):
        raise HTTPException(404, "User template not found")
    progress = await storage.load_progress(user_id)
    if progress is None:
        raise HTTPException(404, f"No data found for user '{user_id}'")
    with open(_USER_TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.get("/api/user/{user_id}/status")
async def user_status(user_id: str):
    data = await reward_api.get_user_status(user_id)
    if data is None:
        raise HTTPException(404, f"No progress found for user '{user_id}'")
    return data


@app.get("/users", response_class=HTMLResponse)
async def users_page():
    """User search page with live search."""
    _USERS_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "users.html")
    if not os.path.exists(_USERS_TEMPLATE):
        raise HTTPException(404, "Users template not found")
    with open(_USERS_TEMPLATE, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/user/progress")
async def user_progress_list(status: str = None, archetype: str = None, search: str = None):
    return await storage.list_progress(status, archetype, search)


@app.get("/api/user/{user_id}/referrals")
async def user_referral_history(user_id: str):
    progress = await storage.load_progress(user_id)
    if progress is None:
        raise HTTPException(404, f"No progress found for user '{user_id}'")
    history = await storage.get_referral_history(user_id)
    return {
        "user_id": user_id,
        "referrals_completed": progress["referrals_completed"],
        "history": history,
    }


# -- Reward handler registration (for future external modules) --

@app.post("/v1/referral/handler")
async def register_handler(data: dict):
    name = data.get("handler", "NoOp")
    return {
        "ok": True,
        "handler": name,
        "note": "RewardHandler is pluggable via reward_api.set_handler() in code. "
                "Set REWARD_PROCESSOR_URL in .env for HTTP-based handler integration."
    }


# -- Overview / Birds-eye view --

_OVERVIEW_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "overview.html")


@app.get("/overview", response_class=HTMLResponse)
async def overview_page():
    if not os.path.exists(_OVERVIEW_TEMPLATE):
        raise HTTPException(404, "Overview template not found")
    with open(_OVERVIEW_TEMPLATE, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/overview")
async def overview_data():
    stats = await storage.get_overview_stats()
    progress = await storage.list_progress()
    recent = await storage.get_recent_confirmations(10)
    return {
        "stats": stats,
        "users": progress,
        "recent_confirmations": recent,
    }


def _run_flow_sync(flow: ReferralFlow, callback_url: str | None):
    """Run the referral flow in a background thread."""
    log = logging.getLogger("referral_engine")
    try:
        flow.kickoff(inputs={})
        log.info(f"Flow complete: {flow.state.job_id} status={flow.state.status} agents={len(_agent_status.get(flow.state.job_id, []))}")
        if flow.state.status == "completed":
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_persist_from_state(flow.state))
            loop.close()
        if callback_url:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(webhook_notify(callback_url, flow.state.model_dump_json()))
            loop.close()
    except Exception as e:
        log.warning(f"Flow failed: {flow.state.job_id} error={e}")
        flow.state.status = "failed"
        flow.state.error = str(e)


async def _persist_from_state(state: ReferralState):
    """Save curve results and user progress to SQLite from a completed ReferralState."""
    try:
        now = datetime.now(timezone.utc).isoformat()

        await storage.save_curve(state.user_id, {
            "archetype": state.tier,
            "reach_score": state.reach_score,
            "advocacy_score": state.advocacy_score,
            "pcu": state.pcu,
            "base_reward": settings.BASE_REWARD,
            "total_budget": state.total_projected_reward,
            "step_count": len(state.milestones),
            "milestones": state.milestones,
            "urgency": state.urgency,
            "penalty_factor": state.penalty_factor,
            "should_ask": True,
            "status": state.status,
            "channel": state.messaging_channel,
            "tone": state.messaging_tone,
            "generated_at": now,
        })

        step_rewards = {}
        for m in state.milestones:
            step_rewards[str(m.get("step", 0))] = m.get("baseline_reward", 0)

        labels = {"Influencer": "Top Referrer", "Broadcaster": "Rising Star",
                  "Fan": "Loyal User", "Newcomer": "Getting Started"}

        await storage.save_progress(state.user_id, {
            "referrals_completed": 0,
            "referrals_target": state.pcu,
            "total_earned": 0.0,
            "current_step": 0,
            "curve_step_rewards": step_rewards,
            "archetype": state.tier,
            "friendly_label": labels.get(state.tier, ""),
            "penalty_factor": state.penalty_factor,
            "reward_unit": settings.REWARD_TYPE,
            "status": "active",
            "reasoning": state.trigger_detail or "",
            "created_at": now,
            "updated_at": now,
        })
    except Exception:
        pass  # Persistence is best-effort, don't fail the main flow


def kickoff():
    flow = ReferralFlow()
    flow.kickoff(inputs={"user_id": "user_123", "raw_events": [], "raw_profile": {}})
    print(flow.state.model_dump_json(indent=2, exclude={"tier"}))
