"""Helpers for enriching stored video metadata."""

from collections.abc import Iterable

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserVideoState, Video
from app.services.video_filters import is_short_video
from app.services.youtube_api import fetch_video_details


async def hydrate_video_metadata(
    db: AsyncSession,
    user: User,
    videos: Iterable[Video],
    *,
    delete_shorts: bool = True,
    max_missing: int | None = None,
) -> set[int]:
    """Fill missing video metadata and optionally delete shorts."""
    videos = list(videos)
    missing_duration_videos = [video for video in videos if not video.duration]
    if max_missing is not None:
        missing_duration_videos = missing_duration_videos[:max_missing]
    details_map: dict[str, dict] = {}

    for idx in range(0, len(missing_duration_videos), 50):
        chunk = missing_duration_videos[idx : idx + 50]
        for item in await fetch_video_details(
            user, [video.youtube_video_id for video in chunk]
        ):
            details_map[item["youtube_video_id"]] = item

    updated = False
    short_ids: set[int] = set()

    for video in videos:
        details = details_map.get(video.youtube_video_id)
        if details:
            video.duration = details.get("duration")
            video.title = details.get("title") or video.title
            video.thumbnail_url = details.get("thumbnail_url") or video.thumbnail_url
            video.published_at = details.get("published_at") or video.published_at
            updated = True

        if is_short_video(video.duration):
            short_ids.add(video.id)

    if delete_shorts and short_ids:
        # Delete dependent rows explicitly so SQLite and the ORM never try to
        # null out the composite PK on user_video_states during flush.
        await db.execute(
            delete(UserVideoState).where(UserVideoState.video_id.in_(short_ids))
        )
        await db.execute(delete(Video).where(Video.id.in_(short_ids)))
        updated = True

    if updated:
        await db.commit()

    return short_ids
