from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FinancialProfileData(BaseModel):
    monthly_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    existing_debt: Optional[float] = None
    credit_score: Optional[int] = None
    credit_utilization: Optional[float] = None
    requested_loan_amount: Optional[float] = None
    loan_tenure_months: Optional[int] = None
    interest_rate: Optional[float] = None
    estimated_emi: Optional[float] = None
    dti: Optional[float] = None
    employment_type: Optional[str] = None
    age: Optional[int] = None

class AIAdviceRequest(BaseModel):
    user_id: Optional[str] = Field(default="user_default")
    financial_data: FinancialProfileData
    user_goal: Optional[str] = Field(default="Assess my financial readiness and ways to optimize borrowing capacity.")

class AIAdviceResponse(BaseModel):
    financial_summary: str
    key_strengths: List[str]
    areas_needing_attention: List[str]
    practical_suggestions: List[str]
    questions_before_borrowing: List[str]
    source: str = "claude-ai"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    saved_to_sheets: bool = False

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str

class AIChatRequest(BaseModel):
    user_id: Optional[str] = Field(default="user_default")
    message: str = Field(..., min_length=1)
    financial_context: Optional[FinancialProfileData] = None
    conversation_history: List[ChatMessage] = Field(default_factory=list)

class AIChatResponse(BaseModel):
    reply: str
    source: str = "claude-ai"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
