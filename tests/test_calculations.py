import pytest
from app.services.emi_service import calculate_emi, compute_emi_details
from app.schemas.emi import EMICalculationRequest
from app.services.credit_service import get_credit_tier, analyze_credit_profile
from app.schemas.credit import CreditAnalysisRequest
from app.services.loan_service import evaluate_loan_eligibility
from app.schemas.loan import LoanEligibilityRequest

class TestEMICalculations:
    def test_normal_loan_emi(self):
        # 10 Lakhs, 10% annual interest, 5 years (60 months)
        # Standard formula gives ~21,247
        emi = calculate_emi(principal=1000000, annual_rate=10.0, tenure_months=60)
        assert 21200 < emi < 21300

    def test_zero_interest_loan(self):
        # 12,000 principal at 0% for 12 months = 1,000/mo
        emi = calculate_emi(principal=12000, annual_rate=0.0, tenure_months=12)
        assert emi == 1000.0

    def test_different_tenures(self):
        principal = 500000
        rate = 9.0
        emi_short = calculate_emi(principal, rate, tenure_months=24)
        emi_long = calculate_emi(principal, rate, tenure_months=84)
        # Shorter tenure should have higher monthly payment
        assert emi_short > emi_long

    def test_large_principal(self):
        # 5 Crore (50,000,000) at 8.5% for 240 months (20 years)
        emi = calculate_emi(principal=50000000, annual_rate=8.5, tenure_months=240)
        assert emi > 400000
        req = EMICalculationRequest(
            principal_loan_amount=50000000,
            annual_interest_rate_percent=8.5,
            loan_tenure_months=240
        )
        res = compute_emi_details(req)
        assert res.total_repayment > res.principal_amount

class TestDTIAndCreditScore:
    def test_credit_score_boundaries(self):
        cat_min, _ = get_credit_tier(300)
        assert cat_min == "Poor"

        cat_max, _ = get_credit_tier(850)
        assert cat_max == "Excellent"

        cat_good, _ = get_credit_tier(720)
        assert cat_good == "Good"

        cat_vgood, _ = get_credit_tier(770)
        assert cat_vgood == "Very Good"

        cat_fair, _ = get_credit_tier(620)
        assert cat_fair == "Fair"

    def test_credit_analyzer_zero_debt(self):
        req = CreditAnalysisRequest(
            credit_score=780,
            credit_utilization_percent=12.0,
            number_of_active_loans=1,
            number_of_credit_cards=2,
            existing_monthly_debt=0.0,
            monthly_income=80000.0,
            payment_history_percent=100.0,
            recent_credit_inquiries=1
        )
        res = analyze_credit_profile(req)
        assert res.dti == 0.0
        assert res.credit_health_category == "Very Good"
        assert len(res.strengths) >= 2

    def test_credit_analyzer_high_debt(self):
        req = CreditAnalysisRequest(
            credit_score=590,
            credit_utilization_percent=85.0,
            number_of_active_loans=5,
            number_of_credit_cards=4,
            existing_monthly_debt=45000.0,
            monthly_income=50000.0,
            payment_history_percent=88.0,
            recent_credit_inquiries=6
        )
        res = analyze_credit_profile(req)
        assert res.dti == 90.0
        assert res.credit_health_category == "Fair"
        assert len(res.areas_for_improvement) >= 2

class TestLoanEligibility:
    def test_high_income_low_debt_eligible(self):
        req = LoanEligibilityRequest(
            monthly_income=150000.0,
            existing_monthly_emis=10000.0,
            employment_type="Salaried",
            employment_duration_years=4.5,
            requested_loan_amount=1000000.0,
            loan_tenure_months=60,
            interest_rate_percent=9.5,
            credit_score=790,
            monthly_expenses=35000.0,
            age=32
        )
        res = evaluate_loan_eligibility(req)
        assert res.eligible is True
        assert res.risk_level in ["Low", "Moderate"]
        assert res.approval_probability_percent >= 70.0
        assert res.estimated_loan_amount > 0

    def test_low_income_high_debt_ineligible(self):
        req = LoanEligibilityRequest(
            monthly_income=30000.0,
            existing_monthly_emis=20000.0,
            employment_type="Freelance",
            employment_duration_years=0.5,
            requested_loan_amount=2000000.0,
            loan_tenure_months=36,
            interest_rate_percent=14.0,
            credit_score=520,
            monthly_expenses=18000.0,
            age=25
        )
        res = evaluate_loan_eligibility(req)
        assert res.eligible is False
        assert res.risk_level in ["High", "Critical"]
        assert len(res.recommendations) > 0
