"""APScheduler configuration for periodic background tasks."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import async_session

logger = logging.getLogger(__name__)


async def _poll_rss_feeds():
    """Periodic task: fetch RSS feeds for all channels to find new videos."""
    from app.models import Channel, User, UserChannel
    from app.services.sync import backfill_videos

    from sqlalchemy import select

    logger.info("Starting RSS polling...")
    async with async_session() as db:
        # Get all users to backfill
        result = await db.execute(select(User))
        users = result.scalars().all()
        for user in users:
            try:
                await backfill_videos(db, user)
            except Exception:
                logger.exception("RSS poll failed for user %d", user.id)
    logger.info("RSS polling completed")


async def _renew_websub():
    """Periodic task: renew WebSub subscriptions before they expire."""
    from app.services.websub import subscribe_all_channels

    logger.info("Renewing WebSub subscriptions...")
    try:
        async with async_session() as db:
            await subscribe_all_channels(db)
    except Exception:
        logger.exception("WebSub renewal failed")


async def _daily_sync():
    """Daily task: sync all users' video feeds and clean up expired videos."""
    from sqlalchemy import select

    from app.models import User
    from app.services.cleanup import cleanup_old_videos
    from app.services.sync import backfill_videos

    logger.info("Starting daily sync...")
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for user in users:
            try:
                await backfill_videos(db, user)
            except Exception:
                logger.exception("Daily sync failed for user %d", user.id)
        await cleanup_old_videos(db)
    logger.info("Daily sync completed")


async def _cleanup():
    """Periodic task: delete old videos."""
    from app.services.cleanup import cleanup_old_videos

    logger.info("Running video cleanup...")
    async with async_session() as db:
        await cleanup_old_videos(db)


def start_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with all periodic tasks."""
    scheduler = AsyncIOScheduler()

    # RSS polling fallback
    scheduler.add_job(
        _poll_rss_feeds,
        "interval",
        minutes=settings.polling_interval_minutes,
        id="poll_rss",
        name="Poll RSS feeds",
        coalesce=True,
        max_instances=1,
    )

    # WebSub renewal (every 4 days, since lease is 5 days)
    scheduler.add_job(
        _renew_websub,
        "interval",
        days=4,
        id="renew_websub",
        name="Renew WebSub subscriptions",
        coalesce=True,
        max_instances=1,
    )

    # Daily sync + cleanup at midnight (jitter ±10min to avoid exact time pressure)
    scheduler.add_job(
        _daily_sync,
        "cron",
        hour=0,
        minute=0,
        jitter=600,
        id="daily_sync",
        name="Daily sync and cleanup",
        coalesce=True,
        max_instances=1,
    )

    # Cleanup old videos daily at configured hour (fallback)
    scheduler.add_job(
        _cleanup,
        "cron",
        hour=settings.cleanup_hour,
        id="cleanup",
        name="Cleanup old videos",
        coalesce=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))
    return scheduler
