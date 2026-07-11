import logging

from app.logging import RedactingFormatter, SecretRedactionFilter, redact_secrets


def test_redact_secrets_removes_supported_secret_formats() -> None:
    value = (
        "token=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi "
        "invite=ABCD-EFGH-JK23 "
        "db=postgresql+asyncpg://dailyenglish:secret@postgres:5432/db "
        "LLM_API_KEY=private-value POSTGRES_PASSWORD=database-secret "
        "ADMIN_UPDATE_COMMAND=/opt/dailyenglish/remote-update.sh"
    )

    result = redact_secrets(value)

    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result
    assert "ABCD-EFGH-JK23" not in result
    assert "dailyenglish:secret" not in result
    assert "private-value" not in result
    assert "database-secret" not in result
    assert "remote-update.sh" not in result


def test_logging_filter_redacts_formatted_arguments() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="invite=%s",
        args=("ABCD-EFGH-JK23",),
        exc_info=None,
    )

    assert SecretRedactionFilter().filter(record) is True
    assert record.getMessage() == "invite=[REDACTED_INVITE]"


def test_formatter_redacts_exception_traceback() -> None:
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    try:
        raise RuntimeError(f"request failed for {token}")
    except RuntimeError as exc:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=(type(exc), exc, exc.__traceback__),
        )

    result = RedactingFormatter("%(message)s").format(record)
    assert token not in result
    assert "[REDACTED_TOKEN]" in result
