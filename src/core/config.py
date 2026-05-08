from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "AI Exam Prep Backend"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    APP_ENV: str = "development"
    PROTOTYPE_MODE: bool = False
    PROTOTYPE_USER_ID: int = 1
    PROTOTYPE_USER_ROLE: str = "admin"

    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/exam_prep"
    )

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    UPLOAD_DIR: str = "uploads"
    FILE_STORAGE_PROVIDER: str = "local"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET_NAME: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    MAX_UPLOAD_FILE_SIZE_MB: int = 15
    LECTURE_NOTE_RELEVANCE_THRESHOLD: float = 0.08
    LECTURE_NOTE_RELEVANCE_MODE: str = "warn"
    MAX_ATTEMPT_DURATION_MINUTES: int = 180
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview"
    GEMINI_TIMEOUT_SECONDS: int = 30
    GEMINI_MAX_RETRIES: int = 2


settings = Settings()
