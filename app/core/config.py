import os
from functools import lru_cache


class Settings:
    """Simple settings loaded from environment.

    Uses dotenv if present (optional) and falls back to sensible defaults.
    """

    def __init__(self) -> None:
        # Attempt to load .env if python-dotenv is available
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            pass

        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/email_elchemy"
        )
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
        self.GOOGLE_TOKEN_PATH: str = os.getenv("GOOGLE_TOKEN_PATH", ".tokens/gmail.json")
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        self.API_KEY: str = os.getenv("API_KEY", "dev-local-key")
        self.PORT: int = int(os.getenv("PORT", "8000"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

