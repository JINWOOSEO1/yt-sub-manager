from app.services.video_filters import (
    SHORTS_MAX_SECONDS,
    is_short_video,
    parse_iso8601_duration_to_seconds,
)


def test_parse_iso8601_duration_to_seconds():
    assert parse_iso8601_duration_to_seconds("PT59S") == 59
    assert parse_iso8601_duration_to_seconds("PT1M30S") == 90
    assert parse_iso8601_duration_to_seconds("PT2H3M4S") == 7384


def test_is_short_video_uses_three_minute_cutoff():
    assert is_short_video("PT3M")
    assert is_short_video("PT2M59S")
    assert not is_short_video("PT3M1S")
    assert SHORTS_MAX_SECONDS == 180
