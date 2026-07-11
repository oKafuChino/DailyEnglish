import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.exceptions import FavoriteContentNotFoundError
from app.services.favorite_service import FavoriteService


def make_service() -> FavoriteService:
    service = FavoriteService(SimpleNamespace())
    service.contents = SimpleNamespace(get_by_id=AsyncMock())
    service.favorites = SimpleNamespace(
        add=AsyncMock(),
        remove=AsyncMock(),
        count_for_user=AsyncMock(),
        list_for_user=AsyncMock(),
    )
    return service


@pytest.mark.asyncio
async def test_add_is_idempotent() -> None:
    service = make_service()
    content_id = uuid.uuid4()
    service.contents.get_by_id.return_value = SimpleNamespace(id=content_id)
    service.favorites.add.side_effect = [True, False]

    assert await service.add(user_id=1, content_id=content_id) is True
    assert await service.add(user_id=1, content_id=content_id) is False


@pytest.mark.asyncio
async def test_add_rejects_deleted_content() -> None:
    service = make_service()
    service.contents.get_by_id.return_value = None

    with pytest.raises(FavoriteContentNotFoundError):
        await service.add(user_id=1, content_id=uuid.uuid4())

    service.favorites.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_page_uses_stable_offset() -> None:
    service = make_service()
    favorites = [SimpleNamespace(id=1)]
    service.favorites.count_for_user.return_value = 12
    service.favorites.list_for_user.return_value = favorites

    items, total = await service.list_page(user_id=7, page=3, page_size=5)

    assert items == favorites
    assert total == 12
    service.favorites.list_for_user.assert_awaited_once_with(
        user_id=7,
        limit=5,
        offset=10,
    )
