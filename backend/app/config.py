import logging
import sys
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_DB_PATH = BACKEND_DIR / "data" / "youtube_sub_manager.db"


class Settings(BaseSettings):
    # Database
    database_url: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_DB_PATH}"

    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT (no default — must be set via env)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # WebSub
    websub_callback_url: str = "http://localhost:8000/api/v1/websub/callback"
    websub_secret: str  # no default — must be set via env

    # Firebase (path to service account JSON)
    firebase_credentials_path: str = ""

    # CORS
    cors_origins: str = "*"

    # Scheduler
    polling_interval_minutes: int = 15
    cleanup_hour: int = 3  # Run cleanup at 3 AM

    model_config = {"env_file": BACKEND_DIR / ".env", "env_prefix": "YSM_"}


settings = Settings()

# Validate critical settings at startup
if not settings.google_client_id or not settings.google_client_secret:
    logger.warning("Google OAuth credentials not set — authentication will fail")

if settings.firebase_credentials_path:
    if not Path(settings.firebase_credentials_path).exists():
        logger.warning(
            "Firebase credentials file not found: %s",
            settings.firebase_credentials_path,
        )

# Ensure data directory exists
data_dir = DEFAULT_SQLITE_DB_PATH.parent
data_dir.mkdir(exist_ok=True)
