import re


def validate_no_pii(result) -> tuple[bool, any]:
    """Reject output containing PII (email, phone)."""
    pii_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        r'\b\d{10,}\b',
    ]
    raw = str(result.raw) if hasattr(result, 'raw') else str(result)
    for pattern in pii_patterns:
        if re.search(pattern, raw):
            return (False, "Output contains PII. Remove all personal information and try again.")
    return (True, result)


def validate_score_range(result) -> tuple[bool, any]:
    """Ensure Reach and Advocacy scores are 0-100."""
    if hasattr(result, 'pydantic') and result.pydantic:
        p = result.pydantic
        if not (0 <= getattr(p, 'reach_score', 50) <= 100):
            return (False, "Reach score out of range (0-100). Recalculate.")
        if not (0 <= getattr(p, 'advocacy_score', 50) <= 100):
            return (False, "Advocacy score out of range (0-100). Recalculate.")
    return (True, result)


def validate_ask_decision(result) -> tuple[bool, any]:
    """Ensure urgency is 0.0-1.0 and should_ask is boolean."""
    if hasattr(result, 'pydantic') and result.pydantic:
        p = result.pydantic
        if not (0.0 <= getattr(p, 'urgency', 0.5) <= 1.0):
            return (False, "Urgency out of range (0.0-1.0). Recalculate.")
        if not isinstance(getattr(p, 'should_ask', False), bool):
            return (False, "should_ask must be boolean.")
    return (True, result)


def validate_curve_budget(result) -> tuple[bool, any]:
    """Ensure total_reward is positive and milestones are non-empty."""
    if hasattr(result, 'pydantic') and result.pydantic:
        p = result.pydantic
        if getattr(p, 'total_reward', 0) < 0:
            return (False, "total_reward cannot be negative. Recalculate curve.")
        if not getattr(p, 'milestones', []):
            return (False, "Curve must contain at least one milestone.")
    return (True, result)
