"""Agent 3: Ask Orchestrator — LLM-powered gate evaluation.

Evaluates referral readiness: checks triggers, gates, cooldowns, and computes
a penalty factor (0.05-1.0) that scales rewards proportionally.
Output validated by validate_ask_decision guardrail.
"""

from crewai import Agent, LLM
from ..config import settings
from ..guardrails import validate_ask_decision


def _create_llm():
    llm = LLM(
        model=settings.OPENAI_MODEL_NAME,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
    )
    llm.supports_function_calling = lambda: False
    return llm


def create_ask_orchestrator() -> Agent:
    return Agent(
        role="Conversion Timing & Gate Specialist",
        goal=(
            "Evaluate whether this user is ready for a referral ask. Check all "
            "gates — account age, advocacy minimum, support ticket status, "
            "ask cooldown, and decline cooldown. Compute a penalty factor "
            "(0.05 to 1.0) that scales down rewards for users who fail gates, "
            "rather than blocking them entirely. Use available trigger and gate "
            "tools for precise threshold comparisons, or reason independently."
        ),
        backstory=(
            "You spent 5 years designing notification timing and gating systems "
            "at a consumer growth startup with 50M+ users. You know that blocking "
            "users outright hurts retention, so you invented a penalty-based system "
            "where every user gets a curve but lower-quality users earn proportionally "
            "less. You check: advocacy floor (penalized below threshold), account age "
            "(new accounts penalized), unresolved support tickets (unhappy users "
            "penalized), ask cooldown (recent asks penalized), and decline cooldown "
            "(recent declines heavily penalized). The global penalty floor is 0.05 "
            "so no one earns zero. Urgency is advocacy / 100, capped at 1.0."
        ),
        tools=[],
        llm=_create_llm(),
        reasoning=False,
        max_iter=4,
        max_execution_time=90,
        guardrail=validate_ask_decision,
        guardrail_max_retries=3,
        verbose=True,
    )
