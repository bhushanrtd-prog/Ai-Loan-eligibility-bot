from typing import List
from app.schemas.emi import EMICalculationRequest, EMICalculationResponse, AmortizationScheduleItem

def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Calculates monthly EMI based on standard amortization formula.
    P * r * (1+r)^n / ((1+r)^n - 1)
    Handles zero interest edge case.
    """
    if tenure_months <= 0:
        raise ValueError("Loan tenure must be at least 1 month.")
    if principal <= 0:
        raise ValueError("Principal must be greater than zero.")

    if annual_rate == 0:
        return round(principal / tenure_months, 2)

    monthly_rate = (annual_rate / 100) / 12
    numerator = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months)
    denominator = ((1 + monthly_rate) ** tenure_months) - 1

    emi = numerator / denominator
    return round(emi, 2)

def generate_amortization_preview(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    monthly_emi: float,
    preview_limit: int = 12
) -> List[AmortizationScheduleItem]:
    """Generates monthly amortization schedule breakdown up to preview_limit months."""
    schedule = []
    remaining_balance = principal
    monthly_rate = (annual_rate / 100) / 12 if annual_rate > 0 else 0

    months_to_run = min(tenure_months, preview_limit)
    for m in range(1, months_to_run + 1):
        if annual_rate > 0:
            interest_component = round(remaining_balance * monthly_rate, 2)
            principal_component = round(monthly_emi - interest_component, 2)
        else:
            interest_component = 0.0
            principal_component = monthly_emi

        # Ensure we don't overpay beyond balance in last month
        if principal_component > remaining_balance or m == tenure_months:
            principal_component = remaining_balance
            total_payment = round(principal_component + interest_component, 2)
            remaining_balance = 0.0
        else:
            total_payment = monthly_emi
            remaining_balance = round(max(0.0, remaining_balance - principal_component), 2)

        schedule.append(
            AmortizationScheduleItem(
                month=m,
                principal_paid=principal_component,
                interest_paid=interest_component,
                total_payment=total_payment,
                remaining_balance=remaining_balance
            )
        )
        if remaining_balance <= 0:
            break

    return schedule

def compute_emi_details(req: EMICalculationRequest) -> EMICalculationResponse:
    principal = req.principal_loan_amount
    annual_rate = req.annual_interest_rate_percent
    tenure_months = req.loan_tenure_months

    monthly_emi = calculate_emi(principal, annual_rate, tenure_months)
    total_repayment = round(monthly_emi * tenure_months, 2)
    total_interest = round(max(0.0, total_repayment - principal), 2)
    interest_ratio = round((total_interest / principal) * 100, 2) if principal > 0 else 0.0

    preview = generate_amortization_preview(principal, annual_rate, tenure_months, monthly_emi)

    return EMICalculationResponse(
        monthly_emi=monthly_emi,
        principal_amount=principal,
        total_interest=total_interest,
        total_repayment=total_repayment,
        interest_to_principal_ratio_percent=interest_ratio,
        tenure_months=tenure_months,
        tenure_years=round(tenure_months / 12, 1),
        amortization_preview=preview
    )
