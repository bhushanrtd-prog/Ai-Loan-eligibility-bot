import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from app.config import settings
from app.schemas.history import HistoryEntry, HistoryResponse

logger = logging.getLogger(__name__)

# Fallback local data directory
LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_STORE_FILE = LOCAL_DATA_DIR / "history_store.json"

def _load_local_store() -> Dict[str, Any]:
    if not LOCAL_STORE_FILE.exists():
        initial = {
            "users": {},
            "records": []
        }
        with open(LOCAL_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2)
        return initial
    try:
        with open(LOCAL_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading local store: {e}")
        return {"users": {}, "records": []}

def _save_local_store(data: Dict[str, Any]):
    try:
        with open(LOCAL_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing to local store: {e}")

class GoogleSheetsService:
    def __init__(self):
        self._client = None
        self._spreadsheet = None
        self._init_attempted = False

    def _get_client(self):
        if self._client:
            return self._client
        if not settings.is_google_sheets_configured:
            return None

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            service_account_val = settings.GOOGLE_SERVICE_ACCOUNT_JSON
            if os.path.exists(service_account_val):
                creds = Credentials.from_service_account_file(service_account_val, scopes=scopes)
            else:
                info = json.loads(service_account_val)
                creds = Credentials.from_service_account_info(info, scopes=scopes)

            self._client = gspread.authorize(creds)
            self._spreadsheet = self._client.open_by_key(settings.GOOGLE_SHEETS_ID)
            self._ensure_sheets_exist()
            return self._client
        except Exception as e:
            logger.warning(f"Google Sheets connection could not be established: {e}. Falling back to local store.")
            return None

    def _ensure_sheets_exist(self):
        """Ensures the required 5 tabs exist with header rows."""
        if not self._spreadsheet:
            return
        tabs = {
            "Users": ["User ID", "Name", "Email", "Occupation", "Created At"],
            "Loan Analyses": ["Record ID", "User ID", "Timestamp", "Income", "Requested Amount", "Tenure Months", "Eligible", "Est Loan", "Est EMI", "DTI", "Risk Level"],
            "Credit Analyses": ["Record ID", "User ID", "Timestamp", "Credit Score", "Category", "Utilization %", "DTI", "Payment History %"],
            "EMI Calculations": ["Record ID", "User ID", "Timestamp", "Principal", "Rate %", "Tenure Months", "Monthly EMI", "Total Interest", "Total Repayment"],
            "AI Advice": ["Record ID", "User ID", "Timestamp", "Summary", "Strengths", "Attention Areas", "Source"]
        }
        existing = [ws.title for ws in self._spreadsheet.worksheets()]
        for tab_name, headers in tabs.items():
            if tab_name not in existing:
                try:
                    ws = self._spreadsheet.add_worksheet(title=tab_name, rows=100, cols=len(headers))
                    ws.append_row(headers)
                except Exception as e:
                    logger.warning(f"Could not initialize sheet {tab_name}: {e}")

    def save_user(self, user_id: str, name: str, email: str = "", occupation: str = "") -> bool:
        client = self._get_client()
        created_at = datetime.utcnow().isoformat()
        saved_cloud = False

        if client and self._spreadsheet:
            try:
                ws = self._spreadsheet.worksheet("Users")
                ws.append_row([user_id, name, email, occupation, created_at])
                saved_cloud = True
            except Exception as e:
                logger.warning(f"Failed to append user to Google Sheet: {e}")

        # Always save to local fallback as well
        local = _load_local_store()
        local["users"][user_id] = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "occupation": occupation,
            "created_at": created_at
        }
        _save_local_store(local)
        return saved_cloud

    def save_loan_analysis(self, user_id: str, data: Dict[str, Any]) -> str:
        record_id = str(uuid.uuid4())[:8]
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        client = self._get_client()
        saved_cloud = False

        if client and self._spreadsheet:
            try:
                ws = self._spreadsheet.worksheet("Loan Analyses")
                ws.append_row([
                    record_id,
                    user_id,
                    timestamp,
                    data.get("factors", {}).get("monthly_income", 0),
                    data.get("estimated_loan_amount", 0),
                    data.get("factors", {}).get("tenure_months", 0),
                    "Eligible" if data.get("eligible") else "Ineligible",
                    data.get("estimated_loan_amount", 0),
                    data.get("estimated_emi", 0),
                    data.get("dti", 0),
                    data.get("risk_level", "Unknown")
                ])
                saved_cloud = True
            except Exception as e:
                logger.warning(f"Google Sheets save_loan_analysis error: {e}")

        # Add to local store
        local = _load_local_store()
        entry = {
            "id": record_id,
            "user_id": user_id,
            "type": "Loan Eligibility",
            "summary": f"{'Eligible' if data.get('eligible') else 'Ineligible'} - Est Loan: ₹{data.get('estimated_loan_amount', 0):,.0f} | EMI: ₹{data.get('estimated_emi', 0):,.0f}",
            "result_badge": f"{data.get('risk_level', 'Moderate')} Risk",
            "badge_color": "success" if data.get("eligible") else "danger",
            "data": data,
            "timestamp": timestamp
        }
        local["records"].insert(0, entry)
        _save_local_store(local)
        return record_id

    def save_credit_analysis(self, user_id: str, data: Dict[str, Any]) -> str:
        record_id = str(uuid.uuid4())[:8]
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        client = self._get_client()

        if client and self._spreadsheet:
            try:
                ws = self._spreadsheet.worksheet("Credit Analyses")
                ws.append_row([
                    record_id,
                    user_id,
                    timestamp,
                    data.get("credit_score"),
                    data.get("credit_health_category"),
                    data.get("credit_utilization_percent"),
                    data.get("dti", 0),
                    data.get("payment_history_percent")
                ])
            except Exception as e:
                logger.warning(f"Google Sheets save_credit_analysis error: {e}")

        local = _load_local_store()
        category = data.get("credit_health_category", "Good")
        badge_colors = {
            "Excellent": "success",
            "Very Good": "success",
            "Good": "info",
            "Fair": "warning",
            "Poor": "danger"
        }
        entry = {
            "id": record_id,
            "user_id": user_id,
            "type": "Credit Analysis",
            "summary": f"Score: {data.get('credit_score')} ({category}) | Utilization: {data.get('credit_utilization_percent')}%",
            "result_badge": category,
            "badge_color": badge_colors.get(category, "info"),
            "data": data,
            "timestamp": timestamp
        }
        local["records"].insert(0, entry)
        _save_local_store(local)
        return record_id

    def save_emi_calculation(self, user_id: str, data: Dict[str, Any]) -> str:
        record_id = str(uuid.uuid4())[:8]
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        client = self._get_client()

        if client and self._spreadsheet:
            try:
                ws = self._spreadsheet.worksheet("EMI Calculations")
                ws.append_row([
                    record_id,
                    user_id,
                    timestamp,
                    data.get("principal_amount"),
                    data.get("annual_rate", 0),
                    data.get("tenure_months"),
                    data.get("monthly_emi"),
                    data.get("total_interest"),
                    data.get("total_repayment")
                ])
            except Exception as e:
                logger.warning(f"Google Sheets save_emi_calculation error: {e}")

        local = _load_local_store()
        entry = {
            "id": record_id,
            "user_id": user_id,
            "type": "EMI Calculation",
            "summary": f"Principal: ₹{data.get('principal_amount', 0):,.0f} | EMI: ₹{data.get('monthly_emi', 0):,.0f}/mo | Total Repayment: ₹{data.get('total_repayment', 0):,.0f}",
            "result_badge": f"₹{data.get('monthly_emi', 0):,.0f}/mo",
            "badge_color": "info",
            "data": data,
            "timestamp": timestamp
        }
        local["records"].insert(0, entry)
        _save_local_store(local)
        return record_id

    def save_ai_advice(self, user_id: str, data: Dict[str, Any]) -> str:
        record_id = str(uuid.uuid4())[:8]
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        client = self._get_client()

        if client and self._spreadsheet:
            try:
                ws = self._spreadsheet.worksheet("AI Advice")
                ws.append_row([
                    record_id,
                    user_id,
                    timestamp,
                    data.get("financial_summary", "")[:200],
                    "; ".join(data.get("key_strengths", [])),
                    "; ".join(data.get("areas_needing_attention", [])),
                    data.get("source", "claude")
                ])
            except Exception as e:
                logger.warning(f"Google Sheets save_ai_advice error: {e}")

        local = _load_local_store()
        entry = {
            "id": record_id,
            "user_id": user_id,
            "type": "AI Advice",
            "summary": data.get("financial_summary", "Comprehensive AI financial evaluation generated.")[:140] + "...",
            "result_badge": "Generated",
            "badge_color": "purple",
            "data": data,
            "timestamp": timestamp
        }
        local["records"].insert(0, entry)
        _save_local_store(local)
        return record_id

    def get_user_history(self, user_id: str) -> HistoryResponse:
        local = _load_local_store()
        records = [HistoryEntry(**rec) for rec in local.get("records", []) if rec.get("user_id") == user_id or user_id == "all" or rec.get("user_id") == "user_default"]

        storage_mode = "Google Sheets & Local Sync" if self._get_client() else "Local Persistent Storage (Sheets Ready)"
        return HistoryResponse(
            user_id=user_id,
            total_records=len(records),
            storage_type=storage_mode,
            records=records
        )

    def delete_record(self, user_id: str, record_id: str) -> bool:
        local = _load_local_store()
        initial_len = len(local.get("records", []))
        local["records"] = [r for r in local.get("records", []) if not (r.get("id") == record_id and (r.get("user_id") == user_id or user_id == "all"))]
        _save_local_store(local)
        return len(local.get("records", [])) < initial_len

sheets_service = GoogleSheetsService()
