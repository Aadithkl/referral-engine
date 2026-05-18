"""Agent 4: Curve Designer — LLM-powered reward curve generation.

Designs a 4-phase valley-surge reward curve: hook → valley → surge → plateau.
Uses archetype ratio params to shape the curve per user tier.
Output validated by validate_curve_budget guardrail.
"""

from crewai import Agent, LLM
from ..config import settings
from ..guardrails import validate_curve_budget


def _create_llm():
    llm = LLM(
        model=settings.OPENAI_MODEL_NAME,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
    )
    llm.supports_function_calling = lambda: False
    return llm


def create_curve_designer() -> Agent:
    return Agent(
        role="Incentive Systems Architect",
        goal=(
            "Design a personalized 4-phase referral reward curve for this user. "
            "The curve has: hook (step 1, highest single reward), valley (ramp "
            "down rewards to build discipline), surge (ramp up rewards approaching "
            "target to create goal-gradient effect), and plateau (capped rewards "
            "post-target to control budget). Use available curve and variable reward "
            "tools for precise math, or design creatively for unique user profiles."
        ),
        backstory=(
            "You have designed loyalty and referral programs for gaming studios "
            "and fintech companies serving 10M+ users. You understand behavioral "
            "economics — the hook creates immediate gratification, the valley tests "
            "commitment (separating casual from committed referrers), the surge "
            "leverages goal-gradient effect (rewards increase as users approach "
            "their target), and the plateau prevents runaway costs. You tailor the "
            "curve shape per archetype: Influencers get moderate hooks with slow "
            "surges (they'll refer anyway), Broadcasters get big hooks with steep "
            "valleys (need early motivation), Fans get gentle curves (already love "
            "the product), and Newcomers get low hooks that grow slowly. You also "
            "recommend the best messaging channel and tone based on urgency."
        ),
        tools=[],
        llm=_create_llm(),
        reasoning=False,
        max_iter=5,
        max_execution_time=120,
        guardrail=validate_curve_budget,
        guardrail_max_retries=3,
        verbose=True,
    )
