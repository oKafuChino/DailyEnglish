import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InviteCode


class InviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        code_digest: str,
        created_by_telegram_id: int,
        expires_at: datetime,
    ) -> InviteCode:
        invite = InviteCode(
            code_digest=code_digest,
            created_by_telegram_id=created_by_telegram_id,
            expires_at=expires_at,
        )
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def get_by_digest_for_update(self, code_digest: str) -> InviteCode | None:
        return await self.session.scalar(
            select(InviteCode).where(InviteCode.code_digest == code_digest).with_for_update()
        )

    async def get_by_id_for_update(self, invite_id: uuid.UUID) -> InviteCode | None:
        return await self.session.scalar(
            select(InviteCode).where(InviteCode.id == invite_id).with_for_update()
        )

    async def list_recent(self, *, limit: int = 10) -> list[InviteCode]:
        result = await self.session.scalars(
            select(InviteCode).order_by(InviteCode.created_at.desc()).limit(limit)
        )
        return list(result)
