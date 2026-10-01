from fastapi import APIRouter
from app.config import settings
from app.services.sheets_service import sheets_service

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health_status():
    sheets_connected = bool(sheets_service._get_client())
    return {
        "status": "healthy",
        "service": "AI Loan Eligibility Checker API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "loan_engine": "operational",
            "credit_analyzer": "operational",
            "emi_calculator": "operational",
            "claude_ai": "connected" if settings.is_claude_configured else "offline-fallback-active",
            "google_sheets": "connected" if sheets_connected else "local-store-fallback-active"
        }
    }
