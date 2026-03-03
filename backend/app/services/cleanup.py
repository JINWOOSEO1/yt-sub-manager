"""Cleanup service for auto-deleting old videos."""

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserPreference, UserVideoState, Video
from app.services.video_retention import RECENT_VIDEO_WINDOW_DAYS, get_video_cutoff

logger = logging.getLogger(__name__)


async def cleanup_old_videos(db: AsyncSession):
    """Delete videos outside the recent-video window or a stricter user preference."""
    # Get the minimum auto_delete_days (most aggressive cleanup).
    result = await db.execute(select(UserPreference.auto_delete_days))
    all_days = [row[0] for row in result.all()]

    min_days = min(all_days) if all_days else RECENT_VIDEO_WINDOW_DAYS
    retention_days = min(min_days, RECENT_VIDEO_WINDOW_DAYS)
    cutoff = get_video_cutoff(retention_days, now=datetime.now(timezone.utc))

    # Delete old user_video_states first (for videos that will be deleted)
    old_video_ids = select(Video.id).where(Video.published_at < cutoff)
    await db.execute(
        delete(UserVideoState).where(UserVideoState.video_id.in_(old_video_ids))
    )

    # Delete old videos
    result = await db.execute(delete(Video).where(Video.published_at < cutoff))
    deleted_count = result.rowcount

    await db.commit()

    if deleted_count > 0:
        logger.info(
            "Cleaned up %d old videos (older than %d days)",
            deleted_count,
            retention_days,
        )
