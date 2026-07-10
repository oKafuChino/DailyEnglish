import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InviteCode, User
from app.db.repositories.audit_logs import AuditLogRepository
from app.db.repositories.invites import InviteRepository
from app.db.repositories.users import UserRepository
from app.domain.enums import UserStatus
from app.domain.time import UTC
from app.exceptions import (
    AlreadyRegisteredError,
    InvalidInviteCodeError,
    InviteCodeExpiredError,
    InviteCodeRedeemedError,
    InviteCodeRevokedError,
    UserBlockedError,
)

INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@dataclass(frozen=True)
class CreatedInvite:
    invite: InviteCode
    plain_code: str


class InviteService:
    def __init__(self, session: AsyncSession, *, pepper: str) -> None:
        if not pepper:
            raise ValueError("Invite-code pepper must not be empty")
        self.invites = InviteRepository(session)
        self.users = UserRepository(session)
        self.audit_logs = AuditLogRepository(session)
        self.pepper = pepper.encode()

    @staticmethod
    def normalize_code(code: str) -> str:
        return code.strip().upper().replace("-", "").replace(" ", "")

    def digest_code(self, code: str) -> str:
        normalized = self.normalize_code(code)
        return hmac.new(self.pepper, normalized.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _new_plain_code() -> str:
        value = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(12))
        return f"{value[:4]}-{value[4:8]}-{value[8:]}"

    async def create_invite(
        self,
        *,
        admin_telegram_id: int,
        valid_for: timedelta = timedelta(days=7),
        now: datetime | None = None,
    ) -> CreatedInvite:
        if not timedelta(hours=1) <= valid_for <= timedelta(days=30):
            raise ValueError("Invite validity must be between 1 hour and 30 days")
        now = now or datetime.now(UTC)
        plain_code = self._new_plain_code()
        invite = await self.invites.create(
            code_digest=self.digest_code(plain_code),
            created_by_telegram_id=admin_telegram_id,
            expires_at=now + valid_for,
        )
        await self.audit_logs.create(
            admin_telegram_id=admin_telegram_id,
            action="invite.created",
            target_type="invite_code",
            target_id=str(invite.id),
            details={"expires_at": invite.expires_at.isoformat()},
        )
        return CreatedInvite(invite=invite, plain_code=plain_code)

    async def redeem(
        self,
        *,
        code: str,
        user: User,
        now: datetime | None = None,
    ) -> InviteCode:
        now = now or datetime.now(UTC)
        if user.status == UserStatus.BLOCKED:
            raise UserBlockedError
        if user.status == UserStatus.ACTIVE:
            raise AlreadyRegisteredError

        normalized = self.normalize_code(code)
        if len(normalized) != 12:
            raise InvalidInviteCodeError
        invite = await self.invites.get_by_digest_for_update(self.digest_code(normalized))
        if invite is None:
            raise InvalidInviteCodeError
        if invite.revoked_at is not None:
            raise InviteCodeRevokedError
        if invite.redeemed_at is not None:
            raise InviteCodeRedeemedError
        if invite.expires_at <= now:
            raise InviteCodeExpiredError

        await self.users.activate(user, at=now)
        invite.redeemed_by_user_id = user.id
        invite.redeemed_at = now
        await self.invites.session.flush()
        return invite

    async def revoke(
        self,
        *,
        invite_id: uuid.UUID,
        admin_telegram_id: int,
        now: datetime | None = None,
    ) -> InviteCode:
        invite = await self.invites.get_by_id_for_update(invite_id)
        if invite is None:
            raise InvalidInviteCodeError
        if invite.redeemed_at is not None:
            raise InviteCodeRedeemedError
        if invite.revoked_at is None:
            invite.revoked_at = now or datetime.now(UTC)
            await self.audit_logs.create(
                admin_telegram_id=admin_telegram_id,
                action="invite.revoked",
                target_type="invite_code",
                target_id=str(invite.id),
            )
        return invite
