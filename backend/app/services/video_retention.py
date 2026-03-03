"""Shared retention rules for stored videos."""

from datetime import datetime, timedelta, timezone

RECENT_VIDEO_WINDOW_DAYS = 14


def get_video_cutoff(
    window_days: int = RECENT_VIDEO_WINDOW_DAYS,
    *,
    now: datetime | None = None,
) -> datetime:
    """Return the cutoff timestamp for retaining recent videos."""
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return reference - timedelta(days=window_days)
