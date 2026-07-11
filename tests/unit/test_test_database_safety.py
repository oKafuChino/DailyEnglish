import pytest

from tests.conftest import RESET_CONFIRMATION, validate_test_database_target


def test_accepts_explicitly_confirmed_test_database() -> None:
    parsed = validate_test_database_target(
        "postgresql+asyncpg://user:password@localhost/dailyenglish_test",
        RESET_CONFIRMATION,
    )

    assert parsed.database == "dailyenglish_test"


def test_rejects_missing_reset_confirmation() -> None:
    with pytest.raises(RuntimeError, match="TEST_DATABASE_RESET_CONFIRM"):
        validate_test_database_target(
            "postgresql+asyncpg://user:password@localhost/dailyenglish_test",
            None,
        )


@pytest.mark.parametrize("database_name", ["dailyenglish", "production", "postgres", ""])
def test_rejects_database_without_test_only_name(database_name: str) -> None:
    with pytest.raises(RuntimeError, match="database name"):
        validate_test_database_target(
            f"postgresql+asyncpg://user:password@localhost/{database_name}",
            RESET_CONFIRMATION,
        )


def test_rejects_non_postgresql_driver() -> None:
    with pytest.raises(RuntimeError, match=r"postgresql\+asyncpg"):
        validate_test_database_target(
            "sqlite+aiosqlite:///dailyenglish_test",
            RESET_CONFIRMATION,
        )
