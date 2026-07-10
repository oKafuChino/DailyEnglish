from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
