import re
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr = SecretStr("")
    owner_telegram_id: int = 0
    database_url: str = "postgresql+asyncpg://dailyenglish:dailyenglish@localhost:5432/dailyenglish"
    invite_code_pepper: SecretStr = SecretStr("")
    app_timezone: str = "Asia/Shanghai"
    default_push_hour: int = Field(default=8, ge=0, le=23)
    default_push_minute: int = Field(default=0, ge=0, le=59)
    log_level: str = "INFO"
    worker_poll_interval_seconds: int = Field(default=60, ge=5, le=3600)
    delivery_retry_minutes: int = Field(default=5, ge=1, le=1440)
    delivery_max_attempts: int = Field(default=3, ge=1, le=20)
    alert_failure_threshold: int = Field(default=3, ge=0, le=1000)
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    rate_limit_default_requests: int = Field(default=30, ge=1, le=1000)
    rate_limit_content_requests: int = Field(default=10, ge=1, le=1000)
    rate_limit_callback_requests: int = Field(default=30, ge=1, le=1000)
    rate_limit_admin_requests: int = Field(default=20, ge=1, le=1000)
    rate_limit_registration_requests: int = Field(default=5, ge=1, le=100)
    rate_limit_registration_window_seconds: int = Field(default=300, ge=30, le=86400)
    admin_update_command: str = ""
    admin_update_timeout_seconds: int = Field(default=600, ge=30, le=3600)
    dictionary_api_key: SecretStr = SecretStr("")
    llm_api_key: SecretStr = SecretStr("")

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown IANA timezone: {value}") from exc
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    def validate_bot_runtime(self) -> None:
        missing: list[str] = []
        if not self.bot_token.get_secret_value():
            missing.append("BOT_TOKEN")
        if self.owner_telegram_id <= 0:
            missing.append("OWNER_TELEGRAM_ID")
        if not self.invite_code_pepper.get_secret_value():
            missing.append("INVITE_CODE_PEPPER")
        if missing:
            raise RuntimeError(f"Missing required runtime settings: {', '.join(missing)}")

        token = self.bot_token.get_secret_value()
        pepper = self.invite_code_pepper.get_secret_value()
        errors: list[str] = []
        if re.fullmatch(r"[0-9]{6,15}:[A-Za-z0-9_-]{20,}", token) is None:
            errors.append("BOT_TOKEN has an invalid format")
        if len(pepper) < 32:
            errors.append("INVITE_CODE_PEPPER must contain at least 32 characters")
        try:
            database_url = make_url(self.database_url)
        except ValueError:
            errors.append("DATABASE_URL is invalid")
        else:
            if database_url.drivername != "postgresql+asyncpg":
                errors.append("DATABASE_URL must use postgresql+asyncpg")
            password = database_url.password or ""
            if password in {"dailyenglish", "change-me", "password"} or len(password) < 12:
                errors.append("DATABASE_URL uses a default or weak password")
        if errors:
            raise RuntimeError("; ".join(errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()
