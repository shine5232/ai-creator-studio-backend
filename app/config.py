from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/openclaw.db"

    # Encryption
    ENCRYPTION_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Auth
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ACCESS_EXPIRE_HOURS: int = 24
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Provider API Keys (defaults from env)
    DOUBAO_API_KEY: str = ""
    DOUBAO_ENDPOINT_ID: str = "ep-m-20260325231513-wj42g"

    WANX_API_KEY: str = ""

    SEEDANCE_API_KEY: str = ""

    GEMINI_API_KEY: str = ""

    ZHIPU_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""

    # Video defaults
    VIDEO_DEFAULT_WIDTH: int = 1080
    VIDEO_DEFAULT_HEIGHT: int = 1920
    VIDEO_DEFAULT_FPS: int = 24

    # Video analysis
    ANALYSIS_MAX_DURATION: int = 600          # max video duration in seconds (10 min)
    ANALYSIS_FRAME_INTERVAL: int = 3          # extract one frame every N seconds
    ANALYSIS_BASE_DIR: str = "data/analysis"  # root dir for analysis files

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""       # empty = fallback to REDIS_URL
    CELERY_RESULT_BACKEND: str = ""   # empty = fallback to REDIS_URL
    CELERY_TASK_ALWAYS_EAGER: bool = False  # for dev testing

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
