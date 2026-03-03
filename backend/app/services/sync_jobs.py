"""In-memory coordination for user-triggered sync jobs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session
from app.models import User

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncJobStatus:
    state: str = "idle"
    message: str = "No sync has been started."
    started_at: datetime | None = None
    finished_at: datetime | None = None
    channel_count: int | None = None
    error: str | None = None


_sync_statuses: dict[int, SyncJobStatus] = {}
_sync_tasks: dict[int, asyncio.Task] = {}
_sync_lock = asyncio.Lock()


def get_sync_status(user_id: int) -> SyncJobStatus:
    return _sync_statuses.get(user_id, SyncJobStatus())


async def start_sync_job(user_id: int) -> SyncJobStatus:
    async with _sync_lock:
        existing = _sync_tasks.get(user_id)
        if existing is not None and not existing.done():
            status = get_sync_status(user_id)
            return SyncJobStatus(
                state=status.state,
                message="Sync is already running.",
                started_at=status.started_at,
                finished_at=status.finished_at,
                channel_count=status.channel_count,
                error=status.error,
            )

        started_at = datetime.now(timezone.utc)
        logger.info("Queueing sync job for user %d", user_id)
        status = SyncJobStatus(
            state="queued",
            message="Sync queued.",
            started_at=started_at,
        )
        _sync_statuses[user_id] = status
        _sync_tasks[user_id] = asyncio.create_task(
            _run_sync_job(user_id, started_at),
            name=f"sync-user-{user_id}",
        )
        return status


async def _run_sync_job(user_id: int, started_at: datetime):
    from app.services.sync import sync_subscriptions

    logger.info("Sync job started for user %d", user_id)
    _sync_statuses[user_id] = SyncJobStatus(
        state="running",
        message="Sync in progress.",
        started_at=started_at,
    )

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError("User not found")

            channel_count = await sync_subscriptions(db, user)
    except Exception as exc:
        logger.exception("Background sync failed for user %d", user_id)
        _sync_statuses[user_id] = SyncJobStatus(
            state="failed",
            message="Sync failed.",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            error=str(exc),
        )
    else:
        logger.info("Sync job succeeded for user %d with %d channels", user_id, channel_count)
        _sync_statuses[user_id] = SyncJobStatus(
            state="succeeded",
            message=f"Synced {channel_count} channels.",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            channel_count=channel_count,
        )
    finally:
        async with _sync_lock:
            task = _sync_tasks.get(user_id)
            if task is asyncio.current_task():
                _sync_tasks.pop(user_id, None)
