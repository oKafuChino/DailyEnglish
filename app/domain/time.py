try:
    from datetime import UTC
except ImportError:  # pragma: no cover - compatibility for local Python 3.10 tooling
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017
