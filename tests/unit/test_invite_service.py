from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.enums import UserStatus
from app.domain.time import UTC
from app.exceptions import (
    InviteCodeExpiredError,
    InviteCodeRedeemedError,
    InviteCodeRevokedError,
)
from app.services.invite_service import InviteService


def make_service() -> InviteService:
    session = SimpleNamespace(flush=AsyncMock())
    service = InviteService(session, pepper="test-pepper")
    service.invites = SimpleNamespace(
        create=AsyncMock(),
        get_by_digest_for_update=AsyncMock(),
        get_by_id_for_update=AsyncMock(),
        session=session,
    )
    service.users = SimpleNamespace(activate=AsyncMock())
    service.audit_logs = SimpleNamespace(create=AsyncMock())
    return service


def test_digest_normalizes_hyphens_spaces_and_case() -> None:
    service = make_service()

    digest = service.digest_code("abcd-efgh-jk23")

    assert digest == service.digest_code(" ABCD EFGH JK23 ")
    assert len(digest) == 64
    assert "ABCD" not in digest


@pytest.mark.asyncio
async def test_create_invite_returns_plain_code_but_persists_only_digest() -> None:
    service = make_service()
    now = datetime(2026, 7, 10, tzinfo=UTC)
    stored_invite = SimpleNamespace(
        id="invite-id",
        expires_at=now + timedelta(days=7),
    )
    service.invites.create.return_value = stored_invite

    result = await service.create_invite(admin_telegram_id=42, now=now)

    assert len(result.plain_code) == 14
    persisted = service.invites.create.await_args.kwargs
    assert persisted["code_digest"] == service.digest_code(result.plain_code)
    assert result.plain_code not in persisted["code_digest"]
    service.audit_logs.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_redeem_activates_user_and_marks_invite_once() -> None:
    service = make_service()
    now = datetime(2026, 7, 10, tzinfo=UTC)
    user = SimpleNamespace(id=7, status=UserStatus.PENDING)
    invite = SimpleNamespace(
        revoked_at=None,
        redeemed_at=None,
        redeemed_by_user_id=None,
        expires_at=now + timedelta(hours=1),
    )
    service.invites.get_by_digest_for_update.return_value = invite

    result = await service.redeem(code="ABCD-EFGH-JK23", user=user, now=now)

    assert result is invite
    assert invite.redeemed_by_user_id == 7
    assert invite.redeemed_at == now
    service.users.activate.assert_awaited_once_with(user, at=now)
    service.invites.session.flush.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("invite_values", "expected_error"),
    [
        ({"revoked_at": True}, InviteCodeRevokedError),
        ({"redeemed_at": True}, InviteCodeRedeemedError),
        ({"expires_at": datetime(2026, 7, 9, tzinfo=UTC)}, InviteCodeExpiredError),
    ],
)
async def test_redeem_rejects_unavailable_invites(invite_values, expected_error) -> None:
    service = make_service()
    now = datetime(2026, 7, 10, tzinfo=UTC)
    values = {
        "revoked_at": None,
        "redeemed_at": None,
        "expires_at": now + timedelta(hours=1),
    }
    values.update(invite_values)
    service.invites.get_by_digest_for_update.return_value = SimpleNamespace(**values)
    user = SimpleNamespace(id=7, status=UserStatus.PENDING)

    with pytest.raises(expected_error):
        await service.redeem(code="ABCD-EFGH-JK23", user=user, now=now)

    service.users.activate.assert_not_awaited()
