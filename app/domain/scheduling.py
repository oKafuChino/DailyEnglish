from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.time import UTC


def next_daily_push_at(
    *,
    timezone_name: str,
    push_time: time,
    after: datetime,
) -> datetime:
    if after.tzinfo is None:
        raise ValueError("Scheduling requires a timezone-aware datetime")
    zone = ZoneInfo(timezone_name)
    local_now = after.astimezone(zone)
    candidate = datetime.combine(local_now.date(), push_time, tzinfo=zone)
    if candidate <= local_now:
        candidate = datetime.combine(
            local_now.date() + timedelta(days=1),
            push_time,
            tzinfo=zone,
        )
    return candidate.astimezone(UTC)


def local_date_for(*, timezone_name: str, moment: datetime) -> date:
    if moment.tzinfo is None:
        raise ValueError("Local-date conversion requires a timezone-aware datetime")
    return moment.astimezone(ZoneInfo(timezone_name)).date()
