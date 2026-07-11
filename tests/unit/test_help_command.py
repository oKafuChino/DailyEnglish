from app.bot.routers.public import build_help_text


def test_help_for_unregistered_user_only_shows_public_commands() -> None:
    text = build_help_text(is_registered=False, is_admin=False)

    assert "/help" in text
    assert "/register <邀请码>" in text
    assert "/word" not in text
    assert "/invite" not in text


def test_help_for_registered_user_shows_learning_commands() -> None:
    text = build_help_text(is_registered=True, is_admin=False)

    assert "/word" in text
    assert "/saved [页码]" in text
    assert "/review" in text
    assert "/setting" in text
    assert "/register" not in text
    assert "/invite" not in text


def test_help_for_admin_includes_user_and_admin_commands() -> None:
    text = build_help_text(is_registered=True, is_admin=True)

    assert "/daily" in text
    assert "👑 管理员指令" in text
    assert "/invite [小时]" in text
    assert "/revoke <邀请码ID>" in text
    assert "/stats" in text
    assert "/update" in text
