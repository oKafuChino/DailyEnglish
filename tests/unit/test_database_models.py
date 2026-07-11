from sqlalchemy import CheckConstraint, UniqueConstraint

from app.db.models import Base


def test_initial_schema_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "admin_audit_logs",
        "content_items",
        "deliveries",
        "favorites",
        "invite_codes",
        "users",
    }


def test_users_have_preferred_difficulty_column() -> None:
    assert "preferred_difficulty" in Base.metadata.tables["users"].columns


def test_favorites_prevent_duplicate_user_content_pairs() -> None:
    constraints = Base.metadata.tables["favorites"].constraints
    names = {item.name for item in constraints if isinstance(item, UniqueConstraint)}
    assert "uq_favorites_user_content" in names


def test_daily_deliveries_have_idempotency_and_date_constraints() -> None:
    constraints = Base.metadata.tables["deliveries"].constraints
    unique_names = {item.name for item in constraints if isinstance(item, UniqueConstraint)}
    check_names = {item.name for item in constraints if isinstance(item, CheckConstraint)}

    assert "uq_deliveries_daily_slot" in unique_names
    assert "ck_deliveries_daily_date_required" in check_names
