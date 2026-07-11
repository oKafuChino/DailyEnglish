from collections import deque

import pytest

from app.bot.middlewares.rate_limit import RateLimitRule, SlidingWindowLimiter


@pytest.mark.asyncio
async def test_sliding_window_blocks_and_reports_retry_time() -> None:
    limiter = SlidingWindowLimiter()
    rule = RateLimitRule(requests=2, window_seconds=10)

    assert await limiter.check((1, "content"), rule, now=0) == (True, 0)
    assert await limiter.check((1, "content"), rule, now=1) == (True, 0)
    assert await limiter.check((1, "content"), rule, now=2) == (False, 8)
    assert await limiter.check((1, "content"), rule, now=11) == (True, 0)


@pytest.mark.asyncio
async def test_rate_limit_buckets_and_users_are_isolated() -> None:
    limiter = SlidingWindowLimiter()
    rule = RateLimitRule(requests=1, window_seconds=60)

    assert await limiter.check((1, "registration"), rule, now=1) == (True, 0)
    blocked = await limiter.check((1, "registration"), rule, now=2)
    assert blocked[0] is False
    assert await limiter.check((1, "content"), rule, now=2) == (True, 0)
    assert await limiter.check((2, "registration"), rule, now=2) == (True, 0)


def test_cleanup_respects_each_buckets_own_window() -> None:
    limiter = SlidingWindowLimiter()
    limiter._events[(1, "registration")] = deque([0])
    limiter._windows[(1, "registration")] = 600
    limiter._events[(1, "content")] = deque([0])
    limiter._windows[(1, "content")] = 60

    limiter._cleanup(300)

    assert (1, "registration") in limiter._events
    assert (1, "content") not in limiter._events
