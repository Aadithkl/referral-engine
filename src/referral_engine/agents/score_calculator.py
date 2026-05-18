"""Agent 2: Score Calculator — LLM-powered with deterministic tools available.

Computes Reach, Advocacy, PCU, and Archetype Tier from normalized user data.
Has access to calculation_tool and tier_mapper_tool as fallbacks.
Output validated by validate_score_range guardrail.
"""

from crewai import Agent, LLM
from ..config import settings
from ..tools.calculation_tools import calculation_tool, tier_mapper_tool
from ..guardrails import validate_score_range


def _create_llm():
    llm = LLM(
        model=settings.OPENAI_MODEL_NAME,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
    )
    llm.supports_function_calling = lambda: False
    return llm


def create_score_calculator() -> Agent:
    return Agent(
        role="Behavioral Quantitative Analyst",
        goal=(
            "Compute Reach (0-100), Advocacy (0-100), Personal Capacity Unit (1+), "
            "and Archetype Tier from the user's normalized profile. Use available "
            "calculation tools when precision matters, or reason independently for "
            "edge cases the tools don't handle."
        ),
        backstory=(
            "You are a data scientist with 8+ years building scoring models for "
            "growth and referral teams at Web3 companies. You understand that "
            "high follower counts alone don't guarantee influence — engagement "
            "rate, account history, and product usage patterns matter equally. "
            "You explain your reasoning for every score and always stay within "
            "0-100 range for reach and advocacy. You classify users into one of "
            "four archetypes: Influencer (high reach + high advocacy), Broadcaster "
            "(high reach + low advocacy), Fan (low reach + high advocacy), or "
            "Newcomer (low reach + low advocacy)."
        ),
        tools=[calculation_tool, tier_mapper_tool],
        llm=_create_llm(),
        reasoning=False,
        max_iter=4,
        max_execution_time=90,
        guardrail=validate_score_range,
        guardrail_max_retries=3,
        verbose=True,
    )
