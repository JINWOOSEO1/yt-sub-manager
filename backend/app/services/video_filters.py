"""Helpers for filtering YouTube videos."""

import re

SHORTS_MAX_SECONDS = 180

_DURATION_RE = re.compile(
    r"^P(?:\d+Y)?(?:\d+M)?(?:\d+D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$"
)


def parse_iso8601_duration_to_seconds(duration: str | None) -> int | None:
    """Convert a YouTube ISO 8601 duration into total seconds."""
    if not duration:
        return None

    match = _DURATION_RE.match(duration)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def is_short_video(duration: str | None) -> bool:
    """Treat videos up to 3 minutes as Shorts."""
    total_seconds = parse_iso8601_duration_to_seconds(duration)
    return total_seconds is not None and total_seconds <= SHORTS_MAX_SECONDS
