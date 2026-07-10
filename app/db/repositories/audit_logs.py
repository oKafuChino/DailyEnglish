from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminAuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        admin_telegram_id: int,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AdminAuditLog:
        log = AdminAuditLog(
            admin_telegram_id=admin_telegram_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
        self.session.add(log)
        await self.session.flush()
        return log
