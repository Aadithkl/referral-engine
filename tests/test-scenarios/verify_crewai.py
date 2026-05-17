"""verify_crewai.py -- Full CrewAI agentic pipeline verification.

Tests: tools -> agents -> flow -> API, with real LLM calls through OpenCode.
Run from project root:  python tests/test-scenarios/verify_crewai.py
"""

import json
import sys
import os
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

PASS = f"{GREEN}PASS{RESET}"
FAIL = f"{RED}FAIL{RESET}"
SKIP = f"{YELLOW}SKIP{RESET}"

DATA_DIR = Path(__file__).resolve().parent / "data"
results = []


def load_persona(name: str) -> dict:
    with open(DATA_DIR / f"{name}.json") as f:
        return json.load(f)


def header(text: str):
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    msg = f"  {status} {name}"
    if detail and not condition:
        msg += f" -- {RED}{detail}{RESET}"
    elif detail:
        msg += f" -- {detail}"
    print(msg)
    results.append({"name": name, "ok": condition, "detail": detail})


# =========================================================================
# LAYER A: Tool Verification (no API key)
# =========================================================================
def layer_a_tools():
    header("LAYER A: Tool Verification (no API key)")

    from referral_engine.tools.database_tools import (
        database_query_tool, http_receive_tool, data_normalizer_tool,
    )
    from referral_engine.tools.twitter_tools import (
        twitter_profile_tool, twitter_tweets_tool, token_refresh_tool,
    )
    from referral_engine.tools.calculation_tools import (
        calculation_tool, tier_mapper_tool, valley_surge_calculator_tool,
        variable_reward_tool, strategy_selector_tool,
    )
    from referral_engine.tools.trigger_tools import (
        trigger_evaluator_tool, gate_checker_tool, user_state_query_tool,
    )

    all_tools = {
        "DatabaseQueryTool": database_query_tool,
        "HttpReceiveTool": http_receive_tool,
        "DataNormalizerTool": data_normalizer_tool,
        "TwitterProfileTool": twitter_profile_tool,
        "TwitterTweetsTool": twitter_tweets_tool,
        "TokenRefreshTool": token_refresh_tool,
        "CalculationTool": calculation_tool,
        "TierMapperTool": tier_mapper_tool,
        "ValleySurgeCalculatorTool": valley_surge_calculator_tool,
        "VariableRewardTool": variable_reward_tool,
        "StrategySelectorTool": strategy_selector_tool,
        "TriggerEvaluatorTool": trigger_evaluator_tool,
        "GateCheckerTool": gate_checker_tool,
        "UserStateQueryTool": user_state_query_tool,
    }

    for name, tool in all_tools.items():
        try:
            ok_name = hasattr(tool, "name")
            ok_desc = hasattr(tool, "description") and bool(tool.description)
            check(f"{name} is CrewAI Tool", ok_name and ok_desc,
                  f"name={getattr(tool, 'name', None)}, desc={getattr(tool, 'description', '')[:40]}...")
        except Exception as e:
            check(f"{name} is CrewAI Tool", False, str(e))

    # Test deterministic tool calls
    print()
    try:
        r = tier_mapper_tool.run(reach=24, advocacy=72)
        check("TierMapperTool.run(reach=24, adv=72) -> Builder",
              r.get("tier") == "Builder", f"got tier={r.get('tier')}")
    except Exception as e:
        check("TierMapperTool.run()", False, str(e))

    try:
        r = calculation_tool.run(
            twitter_followers=5000, twitter_engagement=0.052,
            twitter_following=1200, account_age_days=607,
            total_sessions_90d=95, feature_adoption=8,
            positive_outcomes=15, support_tickets=1, support_resolved=1,
            activity_trend="rising"
        )
        check("CalculationTool.run(power_user)", isinstance(r, dict) and "reach" in r,
              f"reach={r.get('reach')}, advocacy={r.get('advocacy')}")
    except Exception as e:
        check("CalculationTool.run()", False, str(e))

    try:
        r = gate_checker_tool.run(
            account_age_days=607, advocacy_score=94,
            support_tickets_90d=1, support_tickets_resolved=1,
            last_declined_at="",
        )
        check("GateCheckerTool.run() all pass",
              len(r.get("gates_passed", [])) == 4,
              f"passed={r.get('gates_passed')}, blocked={r.get('gates_blocked')}")
    except Exception as e:
        check("GateCheckerTool.run()", False, str(e))

    try:
        r = valley_surge_calculator_tool.run(
            tier="Broadcaster", pcu=96, optimal_zone_min=8, optimal_zone_max=15, urgency=0.85,
        )
        phases = set(m.get("phase") for m in r.get("curve", []))
        check("ValleySurgeCalculatorTool.run() has 4 phases",
              phases == {"hook", "valley", "surge", "plateau"},
              f"phases={phases}, milestones={len(r.get('curve', []))}")
    except Exception as e:
        check("ValleySurgeCalculatorTool.run()", False, str(e))


# =========================================================================
# LAYER B: Agent Instantiation (no API key)
# =========================================================================
def layer_b_agents():
    header("LAYER B: Agent Instantiation (no API key)")

    from referral_engine.agents.signal_parser import create_signal_parser
    from referral_engine.agents.score_calculator import create_score_calculator
    from referral_engine.agents.ask_orchestrator import create_ask_orchestrator
    from referral_engine.agents.curve_designer import create_curve_designer

    agents = {
        "Signal Parser": create_signal_parser,
        "Score Calculator": create_score_calculator,
        "Ask Orchestrator": create_ask_orchestrator,
        "Curve Designer": create_curve_designer,
    }

    created = {}
    for name, factory in agents.items():
        try:
            agent = factory()
            ok_role = bool(agent.role)
            ok_goal = bool(agent.goal)
            ok_backstory = bool(agent.backstory)
            ok_tools = len(agent.tools) >= 3
            ok_guardrail = agent.guardrail is not None
            ok_llm = agent.llm is not None

            all_ok = all([ok_role, ok_goal, ok_backstory, ok_tools, ok_guardrail, ok_llm])
            check(f"{name} instantiation",
                  all_ok,
                  f"role={ok_role} goal={ok_goal} tools={len(agent.tools)} guardrail={ok_guardrail} llm={ok_llm}")
            if all_ok:
                created[name] = agent
        except Exception as e:
            check(f"{name} instantiation", False, str(e))

    return created


# =========================================================================
# LAYER C: Flow Structure (no API key)
# =========================================================================
def layer_c_flow():
    header("LAYER C: Flow Structure (no API key)")

    from referral_engine.main import ReferralFlow

    try:
        flow = ReferralFlow()
        check("ReferralFlow instantiated", True)

        methods = {
            "parse_signals": "@start()",
            "calculate_scores": "@listen(parse_signals)",
            "orchestrate_ask": "@listen(calculate_scores)",
            "route_ask": "@router(orchestrate_ask)",
            "design_curve": "@listen('design_curve')",
            "finalize_held": "@listen('hold')",
        }
        for name, expected in methods.items():
            has_method = hasattr(flow, name)
            check(f"Flow.{name} ({expected})", has_method, "" if has_method else "missing method")

        check("Flow has state attribute", hasattr(flow, "state"), f"type={type(getattr(flow, 'state', None))}")
    except Exception as e:
        check("ReferralFlow structure", False, str(e))


# =========================================================================
# LAYER D-G: Agent kickoff() with LLM (API key required)
# =========================================================================
def layer_d_agent_kickoffs(agents_dict):
    from referral_engine.models import NormalizedProfile, ScoreOutput, AskDecision, CurvePlan
    from referral_engine.state import ReferralState

    agent_tests = [
        {
            "layer": "D",
            "name": "Agent 1: Signal Parser kickoff()",
            "agent_key": "Signal Parser",
            "response_format": NormalizedProfile,
            "messages": (
                "User ID: power_user_001\n"
                "Raw Events (if provided): [{'event_type': 'login', 'payload': {'count': 1}, 'created_at': '2026-05-14T09:00:00Z'}]\n"
                "Raw Profile (if provided): {'name': 'Alice PowerUser', 'twitter_followers': 5000, 'twitter_engagement_rate': 0.052, 'account_age_days': 607, 'total_product_sessions_90d': 95, 'feature_adoption_count': 8, 'support_tickets_90d': 1, 'support_tickets_resolved': 1, 'positive_outcome_events': 15, 'recent_activity_trend': 'rising', 'prior_referrals_total': 8}"
            ),
            "validate": lambda r: (
                r.pydantic is not None
                and r.pydantic.account_age_days > 0
                and r.pydantic.twitter_followers > 0
            ),
            "validate_detail": lambda r: (
                f"age={r.pydantic.account_age_days}, followers={r.pydantic.twitter_followers}, "
                f"sessions={r.pydantic.total_product_sessions_90d}"
            ) if r.pydantic else "no pydantic output",
        },
    ]

    # Agent 2 (needs context from Agent 1)
    signal_agent = agents_dict.get("Signal Parser")
    if signal_agent:
        try:
            r1 = signal_agent.kickoff(
                messages=(
                    "User ID: power_user_001\n"
                    "Raw Events: [{'event_type': 'login', 'payload': {'count': 1}, 'created_at': '2026-05-14T09:00:00Z'}]\n"
                    "Raw Profile: {'name': 'Alice', 'twitter_followers': 5000, 'twitter_engagement_rate': 0.052, 'account_age_days': 607, 'total_product_sessions_90d': 95, 'feature_adoption_count': 8, 'support_tickets_90d': 1, 'support_tickets_resolved': 1, 'positive_outcome_events': 15, 'recent_activity_trend': 'rising', 'prior_referrals_total': 8}"
                ),
                response_format=NormalizedProfile,
            )
            agent_tests.append({
                "layer": "E",
                "name": "Agent 2: Score Calculator kickoff()",
                "agent_key": "Score Calculator",
                "response_format": ScoreOutput,
                "messages": (
                    f"Normalized Profile: {r1.pydantic.model_dump_json()}\n"
                    f"Twitter Followers: {r1.pydantic.twitter_followers}\n"
                    f"Twitter Engagement: {r1.pydantic.twitter_engagement_rate}\n"
                    f"Account Age (days): {r1.pydantic.account_age_days}"
                ),
                "validate": lambda r: (
                    r.pydantic is not None
                    and 0 <= r.pydantic.reach_score <= 100
                    and 0 <= r.pydantic.advocacy_score <= 100
                    and r.pydantic.tier
                ),
                "validate_detail": lambda r: (
                    f"reach={r.pydantic.reach_score}, adv={r.pydantic.advocacy_score}, "
                    f"pcu={r.pydantic.pcu}, tier={r.pydantic.tier}"
                ) if r.pydantic else "no pydantic output",
            })

            # Agent 3 (needs context from Agent 1 + 2)
            r2 = agents_dict["Score Calculator"].kickoff(
                messages=(
                    f"Normalized Profile: {r1.pydantic.model_dump_json()}\n"
                    f"Twitter Followers: {r1.pydantic.twitter_followers}\n"
                    f"Twitter Engagement: {r1.pydantic.twitter_engagement_rate}\n"
                    f"Account Age (days): {r1.pydantic.account_age_days}"
                ),
                response_format=ScoreOutput,
            )
            agent_tests.append({
                "layer": "F",
                "name": "Agent 3: Ask Orchestrator kickoff()",
                "agent_key": "Ask Orchestrator",
                "response_format": AskDecision,
                "messages": (
                    f"Normalized Profile: {r1.pydantic.model_dump_json()}\n"
                    f"Twitter Followers: {r1.pydantic.twitter_followers}\n"
                    f"Twitter Engagement Rate: {r1.pydantic.twitter_engagement_rate}\n"
                    f"Account Age (days): {r1.pydantic.account_age_days}\n"
                    f"Reach Score: {r2.pydantic.reach_score}/100\n"
                    f"Advocacy Score: {r2.pydantic.advocacy_score}/100\n"
                    f"Tier: {r2.pydantic.tier}\n"
                    f"PCU: {r2.pydantic.pcu}\n"
                    f"Prior Referrals This Month: 8\n"
                ),
                "validate": lambda r: (
                    r.pydantic is not None
                    and isinstance(r.pydantic.should_ask, bool)
                    and 0.0 <= r.pydantic.urgency <= 1.0
                ),
                "validate_detail": lambda r: (
                    f"should_ask={r.pydantic.should_ask}, urgency={r.pydantic.urgency}, "
                    f"reasoning={r.pydantic.reasoning[:60]}..."
                ) if r.pydantic else "no pydantic output",
            })

            # Agent 4 (needs context from Agents 1-3)
            r3 = agents_dict["Ask Orchestrator"].kickoff(
                messages=(
                    f"Normalized Profile: {r1.pydantic.model_dump_json()}\n"
                    f"Twitter Followers: {r1.pydantic.twitter_followers}\n"
                    f"Twitter Engagement Rate: {r1.pydantic.twitter_engagement_rate}\n"
                    f"Account Age (days): {r1.pydantic.account_age_days}\n"
                    f"Reach Score: {r2.pydantic.reach_score}/100\n"
                    f"Advocacy Score: {r2.pydantic.advocacy_score}/100\n"
                    f"Tier: {r2.pydantic.tier}\n"
                    f"PCU: {r2.pydantic.pcu}\n"
                    f"Prior Referrals This Month: 8\n"
                ),
                response_format=AskDecision,
            )
            agent_tests.append({
                "layer": "G",
                "name": "Agent 4: Curve Designer kickoff()",
                "agent_key": "Curve Designer",
                "response_format": CurvePlan,
                "messages": (
                    f"User ID: power_user_001\n"
                    f"Tier: {r2.pydantic.tier}\n"
                    f"PCU: {r2.pydantic.pcu}\n"
                    f"Optimal Zone: {r2.pydantic.optimal_zone}\n"
                    f"Reach: {r2.pydantic.reach_score}, Advocacy: {r2.pydantic.advocacy_score}\n"
                    f"Urgency: {r3.pydantic.urgency}\n"
                    f"Trigger Reasoning: {r3.pydantic.reasoning}\n"
                ),
                "validate": lambda r: (
                    r.pydantic is not None
                    and r.pydantic.hook_reward > 0
                    and len(r.pydantic.milestones) > 0
                    and r.pydantic.total_reward > 0
                ),
                "validate_detail": lambda r: (
                    f"hook=${r.pydantic.hook_reward}, milestones={len(r.pydantic.milestones)}, "
                    f"total=${r.pydantic.total_reward}, channel={r.pydantic.channel}"
                ) if r.pydantic else "no pydantic output",
            })
        except Exception as e:
            check("Agent 1: Signal Parser kickoff()", False, str(e))

    # Run agent tests
    for test in agent_tests:
        header(f"LAYER {test['layer']}: {test['name']}")
        agent = agents_dict.get(test["agent_key"])
        if not agent:
            check(test["name"], False, f"Agent '{test['agent_key']}' not found")
            continue
        try:
            t0 = time.time()
            result = agent.kickoff(
                messages=test["messages"],
                response_format=test["response_format"],
            )
            elapsed = time.time() - t0
            ok = test["validate"](result)
            detail = test["validate_detail"](result) if test["validate"](result) else f"FAIL: {test['validate_detail'](result)}"
            detail += f" [{elapsed:.1f}s]"
            check(test["name"], ok, detail)
            if result.usage_metrics:
                print(f"    tokens: {result.usage_metrics}")
        except Exception as e:
            tb = traceback.format_exc()
            check(test["name"], False, f"{type(e).__name__}: {str(e)[:150]}")
            # Print full trace for debugging
            if "AuthenticationError" in type(e).__name__ or "401" in str(e):
                print(f"    {RED}API key / auth issue -- check OPENAI_API_KEY and base_url{RESET}")
            elif "rate limit" in str(e).lower() or "429" in str(e):
                print(f"    {YELLOW}Rate limited -- wait and retry{RESET}")


# =========================================================================
# LAYER H: Full ReferralFlow.kickoff() (API key required)
# =========================================================================
def layer_h_full_flow():
    header("LAYER H: Full ReferralFlow.kickoff() (API key required)")

    from referral_engine.main import ReferralFlow

    try:
        flow = ReferralFlow()
        flow.state.user_id = "power_user_001"
        flow.state.raw_events = [
            {"event_type": "login", "payload": {"count": 1}, "created_at": "2026-05-14T09:00:00Z"},
        ]
        flow.state.raw_profile = {
            "name": "Alice PowerUser",
            "twitter_followers": 5000,
            "twitter_engagement_rate": 0.052,
            "account_age_days": 607,
            "total_product_sessions_90d": 95,
            "feature_adoption_count": 8,
            "support_tickets_90d": 1,
            "support_tickets_resolved": 1,
            "positive_outcome_events": 15,
            "recent_activity_trend": "rising",
            "prior_referrals_total": 8,
        }
        flow.state.job_id = "job_test_full_flow"

        t0 = time.time()
        flow.kickoff(inputs={})
        elapsed = time.time() - t0

        state = flow.state
        check("Full Flow completed", state.status in ("completed", "held"),
              f"status={state.status}")
        check("Flow produced reach_score", state.reach_score > 0,
              f"reach={state.reach_score}")
        check("Flow produced advocacy_score", state.advocacy_score > 0,
              f"advocacy={state.advocacy_score}")
        check("Flow produced tier", bool(state.tier),
              f"tier={state.tier}")
        check("Flow produced should_ask", isinstance(state.should_ask, bool),
              f"should_ask={state.should_ask}")
        if state.should_ask:
            check("Flow produced milestones", len(state.milestones) > 0,
                  f"milestones={len(state.milestones)}")
            check("Flow produced hook_reward", state.hook_reward > 0,
                  f"hook_reward=${state.hook_reward}")

        print(f"\n    [{elapsed:.1f}s] Final State:")
        print(f"    status={state.status} reach={state.reach_score} adv={state.advocacy_score}")
        print(f"    pcu={state.pcu} tier={state.tier} should_ask={state.should_ask}")
        print(f"    urgency={state.urgency} trigger={state.trigger_detail[:80]}")
        if state.should_ask:
            print(f"    hook=${state.hook_reward} milestones={len(state.milestones)} total=${state.total_projected_reward}")
            print(f"    channel={state.messaging_channel} tone={state.messaging_tone}")

        if state.status == "failed":
            check("Flow error", False, state.error)

    except Exception as e:
        check("Full ReferralFlow.kickoff()", False, f"{type(e).__name__}: {str(e)[:200]}")
        traceback.print_exc()


# =========================================================================
# MAIN
# =========================================================================
def main():
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  CREWAI AGENTIC PIPELINE VERIFICATION{RESET}")
    print(f"{BOLD}{CYAN}  Model: kimi-k2.6 via OpenCode API{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")

    layer_a_tools()
    agents = layer_b_agents()
    layer_c_flow()
    layer_d_agent_kickoffs(agents)
    layer_h_full_flow()

    # Summary
    header("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed

    for r in results:
        status_str = f"{GREEN}PASS{RESET}" if r["ok"] else f"{RED}FAIL{RESET}"
        print(f"  {status_str} {r['name']}")

    print(f"\n  {BOLD}Total: {total} | {GREEN}Passed: {passed}{RESET} | {RED}Failed: {failed}{RESET}")

    if failed > 0:
        print(f"\n  {YELLOW}Some tests failed. Check errors above.{RESET}")
    else:
        print(f"\n  {GREEN}All tests passed!{RESET}")

    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
