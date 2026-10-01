import html
from typing import Any

def sanitize_text(text: str) -> str:
    """Escapes HTML characters and strips surrounding whitespace."""
    if not isinstance(text, str):
        return ""
    return html.escape(text.strip())

def validate_positive_number(val: float, field_name: str) -> float:
    if val <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return float(val)

def validate_credit_score(score: int) -> int:
    if not (300 <= score <= 850):
        raise ValueError("Credit score must be between 300 and 850.")
    return int(score)

def validate_percentage(val: float, field_name: str) -> float:
    if not (0 <= val <= 100):
        raise ValueError(f"{field_name} must be between 0% and 100%.")
    return float(val)

def validate_tenure(months: int) -> int:
    if not (1 <= months <= 480):
        raise ValueError("Loan tenure must be between 1 and 480 months.")
    return int(months)
