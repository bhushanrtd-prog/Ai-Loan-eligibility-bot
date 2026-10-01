import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routes import health, loan, credit, emi, ai, history, user
from app.services.sheets_service import _load_local_store, _save_local_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_loan_checker")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seeds initial demonstration user and history records on startup."""
    local = _load_local_store()
    if not local.get("users"):
        local["users"]["user_default"] = {
            "user_id": "user_default",
            "name": "Aditya Sharma",
            "email": "aditya.sharma@example.com",
            "occupation": "Senior Software Engineer",
            "created_at": "2026-09-30T10:00:00Z"
        }
    if not local.get("records"):
        local["records"] = [
            {
                "id": "rec_001",
                "user_id": "user_default",
                "type": "Loan Eligibility",
                "summary": "Eligible estimate: ₹15,00,000 | EMI: ₹32,450/mo",
                "result_badge": "Low Risk",
                "badge_color": "success",
                "data": {
                    "eligible": True,
                    "estimated_loan_amount": 1500000.0,
                    "estimated_emi": 32450.0,
                    "dti": 18.5,
                    "foir": 38.2,
                    "risk_level": "Low",
                    "reasons": ["FOIR within 45% benchmark", "Credit score 780 satisfies prime rules"],
                    "recommendations": ["Maintain disciplined repayment habits."]
                },
                "timestamp": "2026-09-30T10:15:00Z"
            },
            {
                "id": "rec_002",
                "user_id": "user_default",
                "type": "Credit Analysis",
                "summary": "Score: 780 (Very Good) | Utilization: 18%",
                "result_badge": "Very Good",
                "badge_color": "success",
                "data": {
                    "credit_score": 780,
                    "credit_health_category": "Very Good",
                    "credit_utilization_percent": 18.0,
                    "payment_history_percent": 99.0
                },
                "timestamp": "2026-09-29T14:30:00Z"
            },
            {
                "id": "rec_003",
                "user_id": "user_default",
                "type": "EMI Calculation",
                "summary": "Principal: ₹10,00,000 @ 9.5% for 60m | EMI: ₹21,002/mo",
                "result_badge": "₹21,002/mo",
                "badge_color": "info",
                "data": {
                    "monthly_emi": 21002.0,
                    "principal_amount": 1000000.0,
                    "total_interest": 260117.0,
                    "total_repayment": 1260117.0
                },
                "timestamp": "2026-09-28T09:45:00Z"
            }
        ]
        _save_local_store(local)
    logger.info("AI Loan Eligibility Checker API initialized successfully.")
    yield

app = FastAPI(
    title="AI Loan Eligibility Checker API",
    description="Production-grade BFSI Financial Decision-Support & Underwriting Analysis Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Validation Exception Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        msg = err.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}" if field else msg)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation Error",
            "message": "; ".join(errors) if errors else "Invalid request data provided.",
            "details": exc.errors()
        }
    )

# Custom HTTP Exception Handler
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        err_type = detail.get("error", "Error")
        message = detail.get("message", "An error occurred.")
    else:
        err_type = "HTTP Error"
        message = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": err_type,
            "message": message
        }
    )

# Generic Unhandled Exception Handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": "A server error occurred while processing your financial analysis. Please verify your inputs and try again."
        }
    )

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(loan.router, prefix="/api")
app.include_router(credit.router, prefix="/api")
app.include_router(emi.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(user.router, prefix="/api")
