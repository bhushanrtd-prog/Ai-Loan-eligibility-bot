import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "").strip()
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    @property
    def is_claude_configured(self) -> bool:
        return bool(self.CLAUDE_API_KEY and len(self.CLAUDE_API_KEY) > 10)

    @property
    def is_google_sheets_configured(self) -> bool:
        return bool(self.GOOGLE_SHEETS_ID and self.GOOGLE_SERVICE_ACCOUNT_JSON)

settings = Settings()
