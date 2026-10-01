from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class AmortizationScheduleItem(BaseModel):
    month: int
    principal_paid: float
    interest_paid: float
    total_payment: float
    remaining_balance: float

class EMICalculationRequest(BaseModel):
    user_id: Optional[str] = Field(default="user_default")
    principal_loan_amount: float = Field(..., gt=0, description="Principal loan amount in currency units")
    annual_interest_rate_percent: float = Field(..., ge=0, le=100, description="Annual interest rate percentage")
    loan_tenure_months: int = Field(..., gt=0, le=480, description="Loan tenure in months (1 to 480)")

    @field_validator("principal_loan_amount")
    @classmethod
    def validate_principal(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Principal loan amount must be positive.")
        return round(v, 2)

class EMICalculationResponse(BaseModel):
    monthly_emi: float
    principal_amount: float
    total_interest: float
    total_repayment: float
    interest_to_principal_ratio_percent: float
    tenure_months: int
    tenure_years: float
    amortization_preview: List[AmortizationScheduleItem]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    saved_to_sheets: bool = False
