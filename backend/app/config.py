import logging
import os
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_DB_PATH = BACKEND_DIR / "data" / "youtube_sub_manager.db"
DEFAULT_WEBSUB_CALLBACK_PATH = "/api/v1/websub/callback"


def _normalize_database_url(database_url: str) -> str:
    """Convert generic Postgres URLs to SQLAlchemy asyncpg URLs."""
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


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
settings.database_url = _normalize_database_url(settings.database_url)
if (
    settings.websub_callback_url == f"http://localhost:8000{DEFAULT_WEBSUB_CALLBACK_PATH}"
    and os.getenv("RENDER_EXTERNAL_HOSTNAME")
):
    settings.websub_callback_url = (
        f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}{DEFAULT_WEBSUB_CALLBACK_PATH}"
    )

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
