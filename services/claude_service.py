import json
import logging
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from app.config import settings
from app.schemas.ai import AIAdviceResponse, FinancialProfileData, ChatMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ADVICE = """You are a senior BFSI Financial Education Specialist and decision-support assistant.
Your goal is to provide honest, balanced, highly practical financial education based on the user's data.

Guidelines:
1. Provide:
   - A concise financial summary
   - Key strengths
   - Areas that may need attention
   - Practical improvement suggestions
   - Critical questions the user should consider before taking a loan
2. Do NOT guarantee loan approval or lender terms.
3. Do NOT invent missing information.
4. Do NOT present yourself as an actual bank or lender.
5. Clearly distinguish mathematical calculations from general educational guidance.

Return your response in clean JSON format matching this schema:
{
  "financial_summary": "string",
  "key_strengths": ["string", "string"],
  "areas_needing_attention": ["string", "string"],
  "practical_suggestions": ["string", "string"],
  "questions_before_borrowing": ["string", "string"]
}
Only output the JSON object without markdown code blocks or additional text."""

SYSTEM_PROMPT_CHAT = """You are an AI Financial Advisor and BFSI educator for the 'AI Loan Eligibility Checker' platform.
Your purpose is to answer financial questions, clarify concepts (like DTI, FOIR, credit utilization, secured vs unsecured loans), and help users understand their loan affordability.

Guidelines:
- Give clear, friendly, and structured explanations.
- Show mathematical calculations when the user asks about specific numbers or loan amounts.
- Do not guarantee loan approvals or official lender decisions.
- Do not pretend to know confidential lender proprietary algorithms.
- Always include an educational perspective.
- Be concise, helpful, and maintain a professional yet warm tone.
"""

def generate_offline_fallback_advice(data: FinancialProfileData, goal: Optional[str]) -> AIAdviceResponse:
    """Provides high-quality rule-based financial advice when Claude API key is not present."""
    income = data.monthly_income or 0.0
    expenses = data.monthly_expenses or 0.0
    debt = data.existing_debt or 0.0
    score = data.credit_score or 700
    utilization = data.credit_utilization or 30.0
    requested = data.requested_loan_amount or 0.0
    emi = data.estimated_emi or 0.0

    dti = round((debt / income * 100), 1) if income > 0 else 0.0
    savings_rate = round(((income - expenses - debt) / income * 100), 1) if income > 0 else 0.0

    strengths = []
    attentions = []
    suggestions = []
    questions = []

    if score >= 750:
        strengths.append(f"Strong credit score of {score}, placing you in prime borrowing territory.")
    elif score >= 650:
        strengths.append(f"Fair-to-good credit score ({score}) provides standard market access.")
    else:
        attentions.append(f"Sub-optimal credit score of {score} could result in higher risk premia or rejection.")

    if dti <= 35:
        strengths.append(f"Healthy current Debt-to-Income ratio ({dti}%), leaving capacity for strategic leverage.")
    else:
        attentions.append(f"Existing debt obligations consume {dti}% of gross income, limiting fresh borrowing bandwidth.")

    if savings_rate >= 20:
        strengths.append(f"Commendable cash flow surplus of ~{savings_rate}% after expenses and debt servicing.")
    elif savings_rate > 0:
        attentions.append(f"Modest surplus margin ({savings_rate}%). An unexpected emergency could cause financial strain.")
    else:
        attentions.append("Monthly outlays exceed or equal income, indicating zero or negative savings flow.")

    if requested > 0 and emi > 0:
        if emi > (income * 0.4):
            attentions.append(f"Requested loan EMI (₹{emi:,.0f}) is greater than 40% of monthly income.")
            suggestions.append("Opt for a longer tenure or reduce requested principal to keep EMI below 30-35% of income.")
        else:
            strengths.append(f"Estimated new EMI (₹{emi:,.0f}) represents a manageable {round(emi/income*100, 1)}% of your monthly cash flow.")

    suggestions.extend([
        "Establish an emergency fund equivalent to 6 months of mandatory living expenses before taking new credit.",
        "Maintain credit card utilization strictly under 30% on each billing cycle to protect your score.",
        "Compare interest offers (fixed vs. floating) and inquire about prepayment penalty waivers.",
        "Avoid making multiple simultaneous loan applications to prevent inquiry clustering."
    ])

    questions.extend([
        "How secure is your primary income source over the proposed loan tenure?",
        "Will your monthly budget remain resilient if inflation or unexpected healthcare costs increase?",
        "Could you accelerate repayment through bonuses or annual tax refunds?",
        "Have you accounted for ancillary costs like processing fees, stamp duty, and loan insurance?"
    ])

    summary = (
        f"Based on a monthly income of ₹{income:,.0f} and existing debt of ₹{debt:,.0f} (DTI: {dti}%), "
        f"your financial profile shows {'resilient borrowing capacity' if score >= 720 and dti < 40 else 'moderate borrowing readiness requiring cautious debt management'}. "
        f"{'Your requested loan appears financially viable within typical underwriting parameters.' if emi > 0 and emi <= (income * 0.4) else 'Reviewing repayment tenure and existing commitments is advised prior to formal application.'}"
    )

    return AIAdviceResponse(
        financial_summary=summary,
        key_strengths=strengths if strengths else ["Documented income stream and structured financial planning intent."],
        areas_needing_attention=attentions if attentions else ["Maintaining vigilance on recurring discretionary expenditures."],
        practical_suggestions=suggestions,
        questions_before_borrowing=questions,
        source="educational-engine (API key optional)"
    )

def generate_offline_chat_response(message: str, context: Optional[FinancialProfileData]) -> str:
    """Answers common BFSI and loan questions when Claude API key is not configured."""
    msg = message.lower().strip()
    income = context.monthly_income if context else 50000.0
    debt = context.existing_debt if context else 0.0
    score = context.credit_score if context else 720

    if "afford" in msg and ("lakh" in msg or "5" in msg or "loan" in msg or "k" in msg):
        return (
            f"### Loan Affordability Analysis\n\n"
            f"To determine whether you can comfortably afford this loan, lenders look at your **Fixed Obligation to Income Ratio (FOIR)**:\n\n"
            f"- **Your Monthly Income:** ₹{income:,.0f}\n"
            f"- **Recommended Max Total EMI (50% rule):** ₹{income * 0.5:,.0f}/month\n"
            f"- **Existing EMIs:** ₹{debt:,.0f}/month\n"
            f"- **Available Monthly EMI Capacity:** ₹{max(0.0, (income * 0.5) - debt):,.0f}/month\n\n"
            f"**Example Calculation for a ₹5 Lakh Personal Loan:**\n"
            f"- At **12% interest for 3 years (36 months):** Monthly EMI is approximately **₹16,607**.\n"
            f"- At **12% interest for 5 years (60 months):** Monthly EMI drops to approximately **₹11,122**.\n\n"
            f"💡 **Verdict:** If ₹{max(0.0, (income * 0.5) - debt):,.0f} exceeds the EMI, you are in a viable position. Ensure you retain at least 20% of your salary as free cash savings."
        )

    if "dti" in msg or "debt to income" in msg or "reduce" in msg:
        return (
            f"### How to Reduce Your Debt-to-Income (DTI) Ratio\n\n"
            f"Your **Debt-to-Income (DTI)** ratio is calculated as:\n\n"
            f"$$\\text{{DTI}} = \\frac{{\\text{{Monthly Debt Obligations}}}}{{\\text{{Gross Monthly Income}}}} \\times 100$$\n\n"
            f"**Proven Strategies to Lower Your DTI:**\n"
            f"1. **Debt Avalanche or Snowball Method:** Pay off the smallest loans or highest interest credit card balances first to immediately eliminate monthly minimum dues.\n"
            f"2. **Consolidate High-Interest Balances:** Combine multiple short-term loans into a single lower-rate structured loan.\n"
            f"3. **Avoid Taking On New Debt:** Do not finance new consumer electronics or swipe cards for non-essentials.\n"
            f"4. **Increase Verified Income:** Document secondary income streams, incentives, or freelance revenue."
        )

    if "credit utilization" in msg or "utilization" in msg:
        return (
            f"### Understanding Credit Utilization\n\n"
            f"**Credit utilization** is the percentage of your total revolving credit limit currently in use:\n\n"
            f"$$\\text{{Utilization}} = \\frac{{\\text{{Total Credit Card Balances}}}}{{\\text{{Total Credit Limits}}}} \\times 100$$\n\n"
            f"**Key Benchmarks:**\n"
            f"- **Under 10%:** Ideal / Prime tier\n"
            f"- **10% – 30%:** Healthy and recommended by credit bureaus\n"
            f"- **Over 30%:** May begin lowering your credit score\n"
            f"- **Over 50%:** Flags high financial stress to underwriters\n\n"
            f"💡 *Pro-Tip:* Make an interim payment before your statement date so your reported balance remains under 20%."
        )

    if "secured" in msg or "unsecured" in msg:
        return (
            f"### Secured vs. Unsecured Loans\n\n"
            f"| Feature | Secured Loans | Unsecured Loans |\n"
            f"| :--- | :--- | :--- |\n"
            f"| **Collateral** | Required (Home, Gold, Fixed Deposit) | No collateral required |\n"
            f"| **Interest Rate** | Lower (e.g., 8.5% – 10.5%) | Higher (e.g., 10.5% – 22%) |\n"
            f"| **Tenure** | Up to 15 – 30 years | Typically 1 to 5 years |\n"
            f"| **Risk to Borrower** | Loss of asset upon default | Credit score damage & legal recovery |\n"
            f"| **Approval Speed** | Slower (property/asset appraisal) | Faster (income & CIBIL based) |\n\n"
            f"Secured loans are best suited for large long-term investments like property, while unsecured loans suit quick liquidity needs."
        )

    return (
        f"Thank you for asking! In financial decision-making, balancing your monthly obligations against liquid cash flow is paramount. "
        f"With your current profile (Income: ₹{income:,.0f}, Credit Score: {score}), lenders prioritize regular on-time payment track records "
        f"and keeping total debt under 40-50% of your earnings. "
        f"Feel free to ask me to calculate specific EMIs, compare tenures, or explain how to optimize your loan eligibility!"
    )

async def get_claude_financial_advice(data: FinancialProfileData, goal: Optional[str]) -> AIAdviceResponse:
    """Fetches advice from Claude AI or falls back smoothly if API key is not configured."""
    if not settings.is_claude_configured:
        return generate_offline_fallback_advice(data, goal)

    try:
        client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        user_payload = {
            "monthly_income": data.monthly_income,
            "monthly_expenses": data.monthly_expenses,
            "existing_debt": data.existing_debt,
            "credit_score": data.credit_score,
            "credit_utilization": data.credit_utilization,
            "requested_loan_amount": data.requested_loan_amount,
            "loan_tenure_months": data.loan_tenure_months,
            "interest_rate": data.interest_rate,
            "estimated_emi": data.estimated_emi,
            "dti": data.dti,
            "employment_type": data.employment_type,
            "age": data.age,
            "user_goal": goal
        }

        prompt = f"Analyze this user financial profile and provide structured advice:\n{json.dumps(user_payload, indent=2)}"

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=SYSTEM_PROMPT_ADVICE,
            messages=[{"role": "user", "content": prompt}]
        )

        content = message.content[0].text.strip()
        # Clean potential markdown fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        parsed = json.loads(content)
        return AIAdviceResponse(
            financial_summary=parsed.get("financial_summary", "Financial profile reviewed."),
            key_strengths=parsed.get("key_strengths", []),
            areas_needing_attention=parsed.get("areas_needing_attention", []),
            practical_suggestions=parsed.get("practical_suggestions", []),
            questions_before_borrowing=parsed.get("questions_before_borrowing", []),
            source="claude-3-5-sonnet"
        )
    except Exception as e:
        logger.warning(f"Claude API advice call failed or timed out: {e}. Falling back to rule-based advice.")
        return generate_offline_fallback_advice(data, goal)

async def get_claude_chat_response(
    user_message: str,
    context: Optional[FinancialProfileData],
    history: List[ChatMessage]
) -> str:
    """Answers conversational financial questions via Claude or falls back gracefully."""
    if not settings.is_claude_configured:
        return generate_offline_chat_response(user_message, context)

    try:
        client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        messages_payload = []

        # Add context if available
        context_str = ""
        if context:
            context_str = (
                f"\n[Current User Financial Context: Income=₹{context.monthly_income or 0}, "
                f"Existing Debt=₹{context.existing_debt or 0}, Credit Score={context.credit_score or 'N/A'}, "
                f"Requested Loan=₹{context.requested_loan_amount or 'N/A'}]"
            )

        # Include up to last 6 history messages
        for msg in history[-6:]:
            messages_payload.append({
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content
            })

        # Append current user message
        messages_payload.append({
            "role": "user",
            "content": f"{user_message}{context_str}"
        })

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=SYSTEM_PROMPT_CHAT,
            messages=messages_payload
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Claude API chat call encountered error: {e}. Using intelligent fallback.")
        return generate_offline_chat_response(user_message, context)
