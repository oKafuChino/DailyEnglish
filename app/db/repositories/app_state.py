from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppState


class AppStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> str | None:
        return await self.session.scalar(select(AppState.value).where(AppState.key == key))

    async def set(self, key: str, value: str) -> None:
        statement = insert(AppState).values(key=key, value=value)
        statement = statement.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "value": statement.excluded.value,
                "updated_at": func.now(),
            },
        )
        await self.session.execute(statement)
