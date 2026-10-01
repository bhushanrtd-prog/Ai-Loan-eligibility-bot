from fastapi import APIRouter, HTTPException
from app.schemas.credit import CreditAnalysisRequest, CreditAnalysisResponse
from app.services.credit_service import analyze_credit_profile
from app.services.sheets_service import sheets_service

router = APIRouter(prefix="/credit", tags=["Credit Analyzer"])

@router.post("/analyze", response_model=CreditAnalysisResponse)
def analyze_credit(req: CreditAnalysisRequest):
    try:
        response = analyze_credit_profile(req)
        # Save analysis to Google Sheets / persistent storage
        sheets_service.save_credit_analysis(req.user_id, response.model_dump())
        response.saved_to_sheets = True
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail={"error": "Validation Error", "message": str(ve)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Credit Analysis Error", "message": "Failed to analyze credit profile."})
