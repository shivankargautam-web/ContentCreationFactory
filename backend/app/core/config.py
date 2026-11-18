from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Content Factory"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    log_json: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://acf:acf@localhost:5432/acf"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_always_eager: bool = False

    # Security
    jwt_secret_key: SecretStr = SecretStr("change-me-in-production-please-32b")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    token_encryption_key: SecretStr | None = None  # Fernet key for platform OAuth tokens

    # AI providers
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    openai_image_model: str = "gpt-image-1"
    openai_timeout_seconds: float = 60.0
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # Platforms
    youtube_client_id: str | None = None
    youtube_client_secret: SecretStr | None = None
    meta_graph_api_version: str = "v21.0"
    publishing_dry_run: bool = False

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: str = "/tmp/acf-media"
    media_public_base_url: str = "http://localhost:8000/media"  # served by the API when storage_backend=local
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_presign_expiry_seconds: int = 3600

    # Media rendering
    ffmpeg_binary: str = "ffmpeg"
    video_width: int = 1080
    video_height: int = 1920
    enable_image_generation: bool = False

    # Observability
    otel_enabled: bool = False
    otel_service_name: str = "acf-backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Scheduler
    default_timezone: str = "America/New_York"
    publish_dispatch_interval_seconds: int = 60
    analytics_sync_interval_seconds: int = 3600

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg").replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
