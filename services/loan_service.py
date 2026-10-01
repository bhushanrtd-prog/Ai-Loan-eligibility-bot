from typing import List, Dict, Any
from app.schemas.loan import LoanEligibilityRequest, LoanEligibilityResponse
from app.services.emi_service import calculate_emi

def reverse_loan_amount_from_emi(max_emi: float, annual_rate: float, tenure_months: int) -> float:
    """Calculates the maximum principal loan amount supported by a given monthly EMI capacity."""
    if max_emi <= 0 or tenure_months <= 0:
        return 0.0
    if annual_rate == 0:
        return round(max_emi * tenure_months, 2)

    monthly_rate = (annual_rate / 100) / 12
    # P = EMI * ((1+r)^n - 1) / (r * (1+r)^n)
    compounded = (1 + monthly_rate) ** tenure_months
    principal = max_emi * (compounded - 1) / (monthly_rate * compounded)
    return round(max(0.0, principal), 2)

def evaluate_loan_eligibility(req: LoanEligibilityRequest) -> LoanEligibilityResponse:
    income = req.monthly_income
    existing_debt = req.existing_monthly_emis
    expenses = req.monthly_expenses
    requested_amount = req.requested_loan_amount
    tenure_months = req.loan_tenure_months
    annual_rate = req.interest_rate_percent
    score = req.credit_score
    age = req.age
    emp_type = req.employment_type
    emp_duration = req.employment_duration_years

    # 1. Calculate Estimated New EMI
    estimated_emi = calculate_emi(requested_amount, annual_rate, tenure_months)

    # 2. Key Financial Ratios
    dti = round((existing_debt / income) * 100, 2)
    foir = round(((existing_debt + estimated_emi) / income) * 100, 2)
    net_disposable = round(income - existing_debt - expenses - estimated_emi, 2)

    # 3. Maximum Allowable FOIR Threshold (Rule-based underwriting standard)
    # Higher income tiers can afford slightly higher FOIR
    if income >= 150000:
        max_foir_limit = 0.55
    elif income >= 60000:
        max_foir_limit = 0.50
    else:
        max_foir_limit = 0.40

    # Adjust FOIR limit based on credit score
    if score >= 750:
        max_foir_limit += 0.05
    elif score < 600:
        max_foir_limit -= 0.10

    max_eligible_emi = round(max(0.0, (income * max_foir_limit) - existing_debt), 2)
    max_estimated_loan_amount = reverse_loan_amount_from_emi(max_eligible_emi, annual_rate, tenure_months)

    # Cap max estimated loan amount to sensible bounds
    estimated_loan_amount = min(requested_amount, max_estimated_loan_amount) if max_estimated_loan_amount >= requested_amount else max_estimated_loan_amount

    # 4. Underwriting Rules Assessment
    reasons: List[str] = []
    recommendations: List[str] = []
    risk_points = 0  # 0-2 Low, 3-4 Moderate, 5-6 High, >=7 Critical

    # Rule A: FOIR evaluation
    if foir <= (max_foir_limit * 100):
        reasons.append(f"Combined debt obligations (FOIR: {foir}%) are well within the recommended limit of {int(max_foir_limit * 100)}%.")
    elif foir <= (max_foir_limit * 100 + 15):
        reasons.append(f"Total debt burden (FOIR: {foir}%) is elevated relative to the benchmark {int(max_foir_limit * 100)}%.")
        recommendations.append("Consider opting for a longer loan tenure to lower the monthly EMI, or reduce existing debt.")
        risk_points += 2
    else:
        reasons.append(f"Excessive debt-to-income burden: projected obligations ({foir}%) significantly surpass safe borrowing guidelines.")
        recommendations.append("Prioritize clearing active credit card dues or personal loans before applying.")
        risk_points += 4

    # Rule B: Credit Score evaluation
    if score >= 750:
        reasons.append(f"Excellent credit score ({score}) satisfies prime underwriting guidelines.")
    elif score >= 680:
        reasons.append(f"Good credit score ({score}) meets standard eligibility benchmarks.")
    elif score >= 600:
        reasons.append(f"Fair credit score ({score}) is below standard prime lender cut-offs.")
        recommendations.append("Work on bringing your credit score above 720 to secure lower interest rates.")
        risk_points += 2
    else:
        reasons.append(f"Credit score ({score}) is in the subprime category, posing high underwriting resistance.")
        recommendations.append("Establish a 6-12 month track record of zero missed payments to lift your credit score.")
        risk_points += 4

    # Rule C: Net Disposable Income & Emergency buffer
    if net_disposable >= (income * 0.20):
        reasons.append(f"Comfortable post-EMI disposable surplus of ₹{net_disposable:,.2f} per month.")
    elif net_disposable > 0:
        reasons.append(f"Tight post-EMI cash buffer of ₹{net_disposable:,.2f} remaining.")
        recommendations.append("Keep at least 3-6 months worth of essential expenses in liquid savings as an emergency reserve.")
        risk_points += 1
    else:
        reasons.append(f"Negative net disposable cash flow (deficit of ₹{abs(net_disposable):,.2f}). Monthly expenses and debt exceed income.")
        recommendations.append("Requested loan amount is too large for current monthly cash flow.")
        risk_points += 3

    # Rule D: Age & Tenure feasibility
    retirement_age = 65
    borrower_end_age = age + (tenure_months / 12)
    if borrower_end_age > retirement_age:
        reasons.append(f"Loan tenure extends to age {borrower_end_age:.0f}, which crosses standard retirement age of {retirement_age}.")
        recommendations.append("Consider shortening tenure or adding a younger earning co-applicant.")
        risk_points += 2

    # Rule E: Employment stability
    if emp_duration < 1.0:
        reasons.append(f"Employment tenure of {emp_duration} years is relatively brief for conventional underwriting.")
        recommendations.append("Lenders typically prefer at least 1-2 years continuous experience in the same industry.")
        risk_points += 1
    else:
        reasons.append(f"Stable employment profile with {emp_duration} years in {emp_type}.")

    # 5. Final Decision Determination
    is_eligible = (risk_points <= 3) and (max_eligible_emi >= estimated_emi * 0.85) and (score >= 600) and (net_disposable > 0)

    # Determine risk level
    if risk_points <= 1:
        risk_level = "Low"
        approval_prob = 92.0
    elif risk_points <= 3:
        risk_level = "Moderate"
        approval_prob = 74.0
    elif risk_points <= 5:
        risk_level = "High"
        approval_prob = 42.0
    else:
        risk_level = "Critical"
        approval_prob = 18.0

    if not recommendations:
        recommendations.append("Maintain timely EMI payments to preserve your favorable borrowing terms.")
        recommendations.append("Compare offers across multiple lenders to negotiate processing fee waivers.")

    factors = {
        "monthly_income": income,
        "existing_monthly_debt": existing_debt,
        "estimated_emi": estimated_emi,
        "dti_percent": dti,
        "foir_percent": foir,
        "benchmark_max_foir": round(max_foir_limit * 100, 1),
        "net_disposable_income": net_disposable,
        "risk_score_points": risk_points,
        "borrower_end_age": round(borrower_end_age, 1)
    }

    return LoanEligibilityResponse(
        eligible=is_eligible,
        estimated_loan_amount=round(estimated_loan_amount, 2),
        estimated_emi=estimated_emi,
        dti=dti,
        foir=foir,
        net_disposable_income=net_disposable,
        risk_level=risk_level,
        max_eligible_emi=max_eligible_emi,
        approval_probability_percent=approval_prob,
        reasons=reasons,
        recommendations=recommendations,
        factors=factors
    )
