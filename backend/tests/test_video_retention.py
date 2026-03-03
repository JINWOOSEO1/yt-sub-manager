from datetime import datetime, timezone

from app.services.video_retention import RECENT_VIDEO_WINDOW_DAYS, get_video_cutoff


def test_get_video_cutoff_uses_fourteen_day_window_by_default():
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)

    cutoff = get_video_cutoff(now=now)

    assert RECENT_VIDEO_WINDOW_DAYS == 14
    assert cutoff == datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)


def test_get_video_cutoff_accepts_custom_window():
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)

    cutoff = get_video_cutoff(7, now=now)

    assert cutoff == datetime(2026, 2, 24, 12, 0, tzinfo=timezone.utc)
