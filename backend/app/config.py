import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repo root .env regardless of cwd
_THIS_DIR = Path(__file__).resolve().parent  # app/
_BACKEND_DIR = _THIS_DIR.parent              # backend/
_REPO_ROOT = _BACKEND_DIR.parent             # connective/

_ENV_FILES = []
for candidate in [_REPO_ROOT / ".env", _BACKEND_DIR / ".env"]:
    if candidate.exists():
        _ENV_FILES.append(str(candidate))


def _generate_fernet_key() -> str:
    return Fernet.generate_key().decode()


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONNECTIVE_POSTGRES_", case_sensitive=False,
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    user: str = "connective"
    password: str = "connective"
    host: str = "localhost"
    port: int = 5432
    db: str = "connective"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def sync_url(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def db_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONNECTIVE_", case_sensitive=False,
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JWT — auto-generated if not set (safe for local dev, set in prod)
    jwt_secret: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Fernet encryption key — auto-generated if not set
    fernet_key: str = _generate_fernet_key()

    # OpenAI
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o"

    # OAuth - Slack
    slack_client_id: str = ""
    slack_client_secret: str = ""

    # OAuth - GitHub
    github_client_id: str = ""
    github_client_secret: str = ""

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"


postgres_settings = PostgresSettings()
settings = Settings()
