from typing import List, Tuple
from app.schemas.credit import CreditAnalysisRequest, CreditAnalysisResponse, CreditFactor

def get_credit_tier(score: int) -> Tuple[str, str]:
    """
    Returns (category, color_code) according to educational standards:
    300–579 Poor
    580–669 Fair
    670–739 Good
    740–799 Very Good
    800–850 Excellent
    """
    if score >= 800:
        return "Excellent", "#06b6d4"  # cyan
    elif score >= 740:
        return "Very Good", "#10b981"  # emerald
    elif score >= 670:
        return "Good", "#3b82f6"       # blue
    elif score >= 580:
        return "Fair", "#f59e0b"       # amber
    else:
        return "Poor", "#ef4444"       # red

def analyze_credit_profile(req: CreditAnalysisRequest) -> CreditAnalysisResponse:
    score = req.credit_score
    utilization = req.credit_utilization_percent
    payment_hist = req.payment_history_percent
    inquiries = req.recent_credit_inquiries
    active_loans = req.number_of_active_loans
    credit_cards = req.number_of_credit_cards
    income = req.monthly_income or 50000.0
    debt = req.existing_monthly_debt

    category, color = get_credit_tier(score)
    dti = round((debt / income) * 100, 2) if income > 0 else 0.0

    factors: List[CreditFactor] = []
    strengths: List[str] = []
    improvements: List[str] = []
    tips: List[str] = []

    # 1. Payment History Factor (High impact)
    if payment_hist >= 98:
        factors.append(CreditFactor(
            name="Payment History",
            impact="High Positive",
            status="Exceptional",
            description=f"Your on-time payment track record is stellar ({payment_hist}%). This forms ~35% of traditional credit scoring.",
            recommendation="Keep automated payments active so you never miss a billing due date."
        ))
        strengths.append(f"Impeccable on-time payment record ({payment_hist}%)")
    elif payment_hist >= 90:
        factors.append(CreditFactor(
            name="Payment History",
            impact="Moderate Positive",
            status="Acceptable",
            description=f"Payment record is {payment_hist}%. Occasional delayed payments weigh on the score.",
            recommendation="Set up calendar alerts and auto-debit for minimum payments."
        ))
        improvements.append("Ensure 100% on-time payments for the next 12-24 consecutive months.")
    else:
        factors.append(CreditFactor(
            name="Payment History",
            impact="Critical Negative",
            status="At Risk",
            description=f"Frequent late payments ({payment_hist}% on-time). This is the biggest drag on your credit reputation.",
            recommendation="Immediately prioritize bringing any delinquent accounts current."
        ))
        improvements.append("Clear all past-due balances and avoid any late payments.")

    # 2. Credit Utilization Factor (High impact)
    if utilization <= 20:
        factors.append(CreditFactor(
            name="Credit Card Utilization",
            impact="High Positive",
            status="Optimal",
            description=f"Using only {utilization}% of your revolving limit. Lenders view this as disciplined credit management.",
            recommendation="Maintain utilization under 30% across all individual cards and total limits."
        ))
        strengths.append(f"Very low credit utilization ({utilization}%), demonstrating low dependency on revolving credit.")
    elif utilization <= 40:
        factors.append(CreditFactor(
            name="Credit Card Utilization",
            impact="Neutral",
            status="Moderate",
            description=f"Utilization is at {utilization}%. It is within normal boundaries but approaching the 30% benchmark.",
            recommendation="Aim to pay down card balances before the statement generation date."
        ))
        tips.append("Ask card issuers for an eligible credit limit increase without taking a hard inquiry to reduce utilization.")
    else:
        factors.append(CreditFactor(
            name="Credit Card Utilization",
            impact="High Negative",
            status="Strained",
            description=f"High utilization ({utilization}%). Lenders flag high card balances as elevated liquidity risk.",
            recommendation="Make bi-weekly payments or consider debt consolidation to pull utilization under 30%."
        ))
        improvements.append(f"Reduce credit card utilization from {utilization}% to below 30%.")

    # 3. Credit Inquiries (Moderate impact)
    if inquiries <= 1:
        factors.append(CreditFactor(
            name="Recent Inquiries",
            impact="Positive",
            status="Low Activity",
            description=f"{inquiries} inquiry in recent months. Shows you are not rate-shopping frantically.",
            recommendation="Only apply for fresh credit lines when genuinely necessary."
        ))
        strengths.append("Minimal hard inquiries in the past year.")
    elif inquiries <= 3:
        factors.append(CreditFactor(
            name="Recent Inquiries",
            impact="Neutral",
            status="Normal",
            description=f"{inquiries} hard credit inquiries detected recently.",
            recommendation="Space out any new loan or credit card applications by at least 6 months."
        ))
    else:
        factors.append(CreditFactor(
            name="Recent Inquiries",
            impact="Negative",
            status="High Velocity",
            description=f"{inquiries} credit inquiries in a short timeframe. Lenders perceive this as credit-hungry behavior.",
            recommendation="Freeze new credit applications for 6-12 months to let inquiry scores recover."
        ))
        improvements.append(f"Avoid applying for new loans/cards for at least 6 months ({inquiries} recent inquiries).")

    # 4. Credit Portfolio & Active Accounts
    total_accounts = active_loans + credit_cards
    if total_accounts == 0:
        factors.append(CreditFactor(
            name="Credit Mix",
            impact="Neutral",
            status="Thin File",
            description="You have zero active credit lines. Building an established credit history requires active seasoned accounts.",
            recommendation="Consider a secured credit card or consumer durable loan to start establishing history."
        ))
        improvements.append("Build credit seasoning with an active secured card.")
    elif 1 <= total_accounts <= 6:
        factors.append(CreditFactor(
            name="Credit Mix & Accounts",
            impact="Positive",
            status="Balanced",
            description=f"Active mix of {credit_cards} cards and {active_loans} loans shows manageable variety.",
            recommendation="Keep oldest credit accounts open to preserve average account age."
        ))
        strengths.append(f"Healthy and manageable active credit footprint ({total_accounts} active accounts).")
    else:
        factors.append(CreditFactor(
            name="Credit Mix & Accounts",
            impact="Moderate Negative",
            status="Multi-Obligation",
            description=f"{total_accounts} active accounts ({active_loans} loans + {credit_cards} cards) may fragment financial management.",
            recommendation="Consider streamlining or closing unused high-annual-fee credit cards."
        ))
        tips.append("Consolidate multiple small retail/personal loans into one structured loan if interest rates permit.")

    summary = (
        f"Your credit profile sits in the {category} category with a score of {score}. "
        f"Payment reliability is at {payment_hist}% with a credit utilization of {utilization}%. "
        f"Overall credit health indicates {'strong eligibility potential for prime interest rates' if score >= 740 else 'good access to credit with scope for optimization' if score >= 670 else 'caution is advised; focus on debt reduction and on-time consistency before seeking major financing'}."
    )

    if not tips:
        tips = [
            "Keep credit cards with long histories open to maximize average account age.",
            "Review your credit report annually for erroneous reporting or duplicate loan entries.",
            "Strive to pay total statement balances rather than minimum dues to eliminate revolving interest."
        ]

    return CreditAnalysisResponse(
        credit_score=score,
        credit_health_category=category,
        rating_color=color,
        credit_utilization_percent=utilization,
        dti=dti,
        payment_history_percent=payment_hist,
        key_factors=factors,
        summary=summary,
        strengths=strengths,
        areas_for_improvement=improvements if improvements else ["Continue maintaining disciplined payment habits."],
        simulation_tips=tips
    )
