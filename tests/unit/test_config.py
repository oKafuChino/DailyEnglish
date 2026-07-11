import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_accept_valid_runtime_values() -> None:
    settings = Settings(
        _env_file=None,
        bot_token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
        owner_telegram_id=123456789,
        invite_code_pepper="a-secure-pepper-with-at-least-32-characters",
        database_url=(
            "postgresql+asyncpg://dailyenglish:secure-password-123@localhost/dailyenglish"
        ),
        app_timezone="Asia/Shanghai",
    )

    settings.validate_bot_runtime()
    assert settings.log_level == "INFO"


def test_settings_reject_unknown_timezone() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_timezone="Mars/Olympus_Mons")


def test_runtime_validation_lists_missing_secrets() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(RuntimeError, match="BOT_TOKEN.*OWNER_TELEGRAM_ID.*INVITE_CODE_PEPPER"):
        settings.validate_bot_runtime()


def test_runtime_validation_rejects_weak_or_default_credentials() -> None:
    settings = Settings(
        _env_file=None,
        bot_token="not-a-token",
        owner_telegram_id=123456789,
        invite_code_pepper="too-short",
    )

    with pytest.raises(RuntimeError, match="BOT_TOKEN.*INVITE_CODE_PEPPER.*weak password"):
        settings.validate_bot_runtime()
