import logging
import re

TOKEN_PATTERN = re.compile(r"\b[0-9]{6,15}:[A-Za-z0-9_-]{20,}\b")
INVITE_PATTERN = re.compile(
    r"\b[A-HJ-NP-Z2-9]{4}(?:[- ]?[A-HJ-NP-Z2-9]{4}){2}\b",
    re.IGNORECASE,
)
DATABASE_URL_PATTERN = re.compile(
    r"postgresql(?:\+asyncpg)?://[^:\s]+:[^@\s]+@",
    re.IGNORECASE,
)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(BOT_TOKEN|INVITE_CODE_PEPPER|POSTGRES_PASSWORD|DATABASE_URL|"
    r"LLM_API_KEY|DICTIONARY_API_KEY)=([^\s]+)"
)


def redact_secrets(value: str) -> str:
    value = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", value)
    value = INVITE_PATTERN.sub("[REDACTED_INVITE]", value)
    value = DATABASE_URL_PATTERN.sub("postgresql+asyncpg://***:***@", value)
    return SECRET_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_secrets(super().format(record))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SecretRedactionFilter())
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )
