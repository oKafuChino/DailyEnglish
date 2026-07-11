import asyncio
import math
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings, get_settings


@dataclass(frozen=True)
class RateLimitRule:
    requests: int
    window_seconds: int


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[int, str], deque[float]] = defaultdict(deque)
        self._windows: dict[tuple[int, str], int] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = monotonic()

    async def check(
        self,
        key: tuple[int, str],
        rule: RateLimitRule,
        *,
        now: float | None = None,
    ) -> tuple[bool, int]:
        now = monotonic() if now is None else now
        cutoff = now - rule.window_seconds
        async with self._lock:
            events = self._events[key]
            self._windows[key] = rule.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= rule.requests:
                retry_after = max(1, math.ceil(events[0] + rule.window_seconds - now))
                return False, retry_after
            events.append(now)
            if now - self._last_cleanup >= 300:
                self._cleanup(now)
                self._last_cleanup = now
            return True, 0

    def _cleanup(self, now: float) -> None:
        stale = [
            key
            for key, events in self._events.items()
            if not events or events[-1] <= now - self._windows.get(key, 0)
        ]
        for key in stale:
            self._events.pop(key, None)
            self._windows.pop(key, None)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        limiter: SlidingWindowLimiter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.limiter = limiter or SlidingWindowLimiter()
        self._last_notice: dict[tuple[int, str], float] = {}

    def _get_rule(self, name: str) -> RateLimitRule:
        rules = {
            "default": RateLimitRule(
                self.settings.rate_limit_default_requests,
                self.settings.rate_limit_window_seconds,
            ),
            "content": RateLimitRule(
                self.settings.rate_limit_content_requests,
                self.settings.rate_limit_window_seconds,
            ),
            "callback": RateLimitRule(
                self.settings.rate_limit_callback_requests,
                self.settings.rate_limit_window_seconds,
            ),
            "admin": RateLimitRule(
                self.settings.rate_limit_admin_requests,
                self.settings.rate_limit_window_seconds,
            ),
            "registration": RateLimitRule(
                self.settings.rate_limit_registration_requests,
                self.settings.rate_limit_registration_window_seconds,
            ),
        }
        return rules.get(name, rules["default"])

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)) or event.from_user is None:
            return await handler(event, data)

        handler_object = data.get("handler", data)
        bucket = str(get_flag(handler_object, "rate_limit", default="default"))
        key = (event.from_user.id, bucket)
        allowed, retry_after = await self.limiter.check(key, self._get_rule(bucket))
        if allowed:
            return await handler(event, data)

        text = f"请求过于频繁，请在 {retry_after} 秒后重试。"
        now = monotonic()
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        elif now - self._last_notice.get(key, 0) >= 5:
            self._last_notice[key] = now
            await event.answer(text)
        if len(self._last_notice) > 10_000:
            cutoff = now - self.settings.rate_limit_registration_window_seconds
            self._last_notice = {
                notice_key: timestamp
                for notice_key, timestamp in self._last_notice.items()
                if timestamp > cutoff
            }
        return None
