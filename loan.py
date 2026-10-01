from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class LoanEligibilityRequest(BaseModel):
    user_id: Optional[str] = Field(default="user_default", description="User identifier for history tracking")
    monthly_income: float = Field(..., gt=0, description="Gross monthly income in currency units (e.g., INR)")
    existing_monthly_emis: float = Field(default=0.0, ge=0, description="Total existing monthly EMIs")
    employment_type: str = Field(..., description="Employment type: Salaried, Self-Employed, Business, etc.")
    employment_duration_years: float = Field(..., ge=0, description="Years in current job/business")
    requested_loan_amount: float = Field(..., gt=0, description="Requested principal loan amount")
    loan_tenure_months: int = Field(..., gt=0, le=480, description="Loan duration in months (up to 40 years)")
    interest_rate_percent: float = Field(..., ge=0, le=100, description="Annual interest rate in %")
    credit_score: int = Field(..., ge=300, le=850, description="CIBIL / FICO credit score (300-850)")
    monthly_expenses: float = Field(default=0.0, ge=0, description="Estimated essential monthly expenses")
    age: int = Field(..., ge=18, le=100, description="Borrower age (must be at least 18)")

    @field_validator("monthly_income")
    @classmethod
    def validate_income(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Monthly income must be greater than zero.")
        return round(v, 2)

    @field_validator("credit_score")
    @classmethod
    def validate_credit_score(cls, v: int) -> int:
        if v < 300 or v > 850:
            raise ValueError("Credit score must be between 300 and 850.")
        return v

class LoanEligibilityResponse(BaseModel):
    eligible: bool
    estimated_loan_amount: float
    estimated_emi: float
    dti: float
    foir: float
    net_disposable_income: float
    risk_level: str
    max_eligible_emi: float
    approval_probability_percent: float
    reasons: List[str]
    recommendations: List[str]
    factors: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    saved_to_sheets: bool = False
