"""Agent 1: Signal Parser — ingest, normalize, and enrich user data."""

from crewai import Agent, LLM
from crewai.agent.planning_config import PlanningConfig
from ..config import settings
from ..tools.database_tools import (
    database_query_tool, http_receive_tool, data_normalizer_tool,
)
from ..tools.twitter_tools import twitter_profile_tool, token_refresh_tool
from ..guardrails import validate_no_pii


def _create_llm():
    llm = LLM(
        model=settings.OPENAI_MODEL_NAME,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
    )
    llm.supports_function_calling = lambda: False
    return llm


def create_signal_parser() -> Agent:
    return Agent(
        role="Schema-Agnostic Data Integration Engineer",
        goal=(
            "Ingest and normalize heterogeneous user data from PostgreSQL or HTTP "
            "payload into a clean, structured profile; fetch supplementary Twitter "
            "data when a connected social account exists; manage OAuth token lifecycle "
            "(refresh expired tokens silently)."
        ),
        backstory=(
            "You have 10+ years in data engineering, specializing in ETL pipelines "
            "that handle inconsistent schemas. You have built ingestion systems for "
            "platforms processing millions of user records. You always validate field "
            "types, flag missing data explicitly, and never assume field names exist. "
            "You also manage OAuth token hygiene — checking expiration, refreshing "
            "tokens when needed, and encrypting/decrypting stored credentials."
        ),
        tools=[],
        llm=_create_llm(),
        reasoning=False,
        max_iter=3,
        max_execution_time=90,
        guardrail=validate_no_pii,
        guardrail_max_retries=3,
        verbose=True,
    )
