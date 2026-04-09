from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/job_scanner"

    # OpenAI
    OPENAI_API_KEY: str = ""
    CHAT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "job-scanner"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # ChromaDB
    CHROMADB_PATH: str = "./chroma_data"

    # Crawler
    CRAWL_DELAY_MIN: float = 1.0
    CRAWL_DELAY_MAX: float = 2.0
    CRAWL_USER_AGENT: str = "JobScanner/1.0"
    TARGET_KEYWORDS: list[str] = ["AI Engineer", "ML Engineer", "백엔드"]

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # Auth
    AUTH_SECRET_KEY: str = "change-me-in-production-use-secrets-token-hex-32"
    AUTH_TOKEN_MAX_AGE: int = 86400  # 24 hours in seconds

    # General
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
