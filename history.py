from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime

class HistoryEntry(BaseModel):
    id: str
    user_id: str
    type: str
    summary: str
    result_badge: str
    badge_color: str
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class HistoryResponse(BaseModel):
    user_id: str
    total_records: int
    storage_type: str = "google_sheets"
    records: List[HistoryEntry]
