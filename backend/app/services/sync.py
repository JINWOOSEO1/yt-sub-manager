"""Sync subscriptions and backfill videos from YouTube."""

import logging
from datetime import datetime, timezone

import httpx
from defusedxml import ElementTree
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Channel, User, UserChannel, Video
from app.services.video_filters import is_short_video
from app.services.video_metadata import hydrate_video_metadata
from app.services.video_retention import get_video_cutoff
from app.services.youtube_api import fetch_video_details

logger = logging.getLogger(__name__)

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
ATOM_NS = "http://www.w3.org/2005/Atom"
MEDIA_NS = "http://search.yahoo.com/mrss/"
YT_NS = "http://www.youtube.com/xml/schemas/2015"


async def sync_subscriptions(db: AsyncSession, user: User) -> int:
    """Fetch user's YouTube subscriptions and sync to DB. Returns channel count."""
    from app.services.youtube_api import fetch_subscriptions

    logger.info("Starting subscription sync for user %d", user.id)
    subs = await fetch_subscriptions(user)
    if not subs:
        logger.info("User %d has no subscriptions returned by YouTube API", user.id)
        await backfill_videos(db, user)
        return 0

    yt_ids = [sub["youtube_channel_id"] for sub in subs]
    result = await db.execute(
        select(Channel).where(Channel.youtube_channel_id.in_(yt_ids))
    )
    channels_by_yt_id = {
        channel.youtube_channel_id: channel for channel in result.scalars().all()
    }

    new_channels: list[Channel] = []
    for sub in subs:
        yt_id = sub["youtube_channel_id"]
        channel = channels_by_yt_id.get(yt_id)
        if channel is None:
            channel = Channel(
                youtube_channel_id=yt_id,
                title=sub["title"],
                thumbnail_url=sub.get("thumbnail_url"),
            )
            db.add(channel)
            channels_by_yt_id[yt_id] = channel
            new_channels.append(channel)
        else:
            channel.title = sub["title"]
            if sub.get("thumbnail_url"):
                channel.thumbnail_url = sub["thumbnail_url"]

    if new_channels:
        await db.flush()

    channel_ids = [channels_by_yt_id[sub["youtube_channel_id"]].id for sub in subs]
    result = await db.execute(
        select(UserChannel.channel_id).where(
            UserChannel.user_id == user.id,
            UserChannel.channel_id.in_(channel_ids),
        )
    )
    linked_channel_ids = set(result.scalars().all())

    for channel_id in channel_ids:
        if channel_id not in linked_channel_ids:
            db.add(UserChannel(user_id=user.id, channel_id=channel_id))

    await db.commit()

    # Backfill recent videos for all channels
    await backfill_videos(db, user)

    logger.info("Subscription sync finished for user %d with %d channels", user.id, len(subs))
    return len(subs)


async def backfill_videos(db: AsyncSession, user: User):
    """Fetch recent videos from RSS feeds for all user's channels."""
    cutoff = get_video_cutoff()
    result = await db.execute(
        select(Channel)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(UserChannel.user_id == user.id)
    )
    channels = result.scalars().all()
    logger.info("Backfilling videos for user %d across %d channels", user.id, len(channels))

    async with httpx.AsyncClient(timeout=30) as client:
        for channel in channels:
            try:
                await _fetch_rss_videos(db, client, user, channel)
            except Exception:
                logger.exception(
                    "Failed to fetch RSS for channel %s", channel.youtube_channel_id
                )

    # Existing videos created before duration tracking need one-time hydration.
    result = await db.execute(
        select(Video)
        .join(Channel, Video.channel_id == Channel.id)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(
            UserChannel.user_id == user.id,
            Video.duration.is_(None),
            Video.published_at >= cutoff,
        )
        .order_by(Video.published_at.desc())
        .limit(100)
    )
    await hydrate_video_metadata(db, user, result.scalars().all())

    await db.commit()
    logger.info("Finished backfilling recent videos for user %d", user.id)


async def _fetch_rss_videos(
    db: AsyncSession, client: httpx.AsyncClient, user: User, channel: Channel
):
    """Parse YouTube RSS feed and insert new videos."""
    cutoff = get_video_cutoff()
    url = YOUTUBE_RSS_URL.format(channel_id=channel.youtube_channel_id)
    resp = await client.get(url)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)

    entries_to_create: list[dict] = []

    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        video_id_el = entry.find(f"{{{YT_NS}}}videoId")
        if video_id_el is None:
            continue
        video_id = video_id_el.text

        title_el = entry.find(f"{{{ATOM_NS}}}title")
        published_el = entry.find(f"{{{ATOM_NS}}}published")
        media_group = entry.find(f"{{{MEDIA_NS}}}group")

        thumbnail_url = None
        if media_group is not None:
            thumb_el = media_group.find(f"{{{MEDIA_NS}}}thumbnail")
            if thumb_el is not None:
                thumbnail_url = thumb_el.get("url")

        published_at = datetime.now(timezone.utc)
        if published_el is not None and published_el.text:
            published_at = datetime.fromisoformat(
                published_el.text.replace("Z", "+00:00")
            )

        # Skip videos older than the recent-video window.
        if published_at < cutoff:
            continue

        entries_to_create.append(
            {
                "youtube_video_id": video_id,
                "channel_id": channel.id,
                "title": title_el.text if title_el is not None else "Unknown",
                "thumbnail_url": thumbnail_url,
                "published_at": published_at,
            }
        )

    if not entries_to_create:
        channel.last_checked_at = datetime.now(timezone.utc)
        return

    result = await db.execute(
        select(Video.youtube_video_id).where(
            Video.youtube_video_id.in_(
                [entry["youtube_video_id"] for entry in entries_to_create]
            )
        )
    )
    existing_video_ids = set(result.scalars().all())
    entries_to_create = [
        entry
        for entry in entries_to_create
        if entry["youtube_video_id"] not in existing_video_ids
    ]

    if not entries_to_create:
        channel.last_checked_at = datetime.now(timezone.utc)
        return

    details_map = {
        item["youtube_video_id"]: item
        for item in await fetch_video_details(
            user,
            [entry["youtube_video_id"] for entry in entries_to_create]
        )
    }

    videos_to_add: list[Video] = []
    for entry_data in entries_to_create:
        details = details_map.get(entry_data["youtube_video_id"])
        duration = details.get("duration") if details else None
        published_at = (
            details.get("published_at")
            if details and details.get("published_at")
            else entry_data["published_at"]
        )
        if published_at < cutoff:
            continue
        if is_short_video(duration):
            continue

        videos_to_add.append(
            Video(
                youtube_video_id=entry_data["youtube_video_id"],
                channel_id=entry_data["channel_id"],
                title=details.get("title") if details else entry_data["title"],
                thumbnail_url=(
                    details.get("thumbnail_url")
                    if details
                    else entry_data["thumbnail_url"]
                ),
                published_at=published_at,
                duration=duration,
            )
        )

    if videos_to_add:
        db.add_all(videos_to_add)

    channel.last_checked_at = datetime.now(timezone.utc)
