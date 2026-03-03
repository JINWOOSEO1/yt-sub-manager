from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_utils import get_current_user
from app.database import get_db
from app.models import Channel, User, UserChannel
from app.schemas import ChannelOut, SyncStatusOut
from app.services.sync_jobs import get_sync_status, start_sync_job
from app.services.youtube_api import (
    ReauthenticationRequiredError,
    ensure_refreshable_credentials,
)

router = APIRouter()


@router.get("", response_model=list[ChannelOut])
async def list_channels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all subscribed channels for the current user."""
    result = await db.execute(
        select(Channel)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(UserChannel.user_id == user.id)
        .order_by(Channel.title)
    )
    return result.scalars().all()


def _serialize_sync_status(status_obj) -> SyncStatusOut:
    return SyncStatusOut(
        state=status_obj.state,
        message=status_obj.message,
        started_at=status_obj.started_at,
        finished_at=status_obj.finished_at,
        channel_count=status_obj.channel_count,
        error=status_obj.error,
    )


@router.post("/sync", response_model=SyncStatusOut, status_code=status.HTTP_202_ACCEPTED)
async def sync_channels(
    user: User = Depends(get_current_user),
):
    """Queue subscription sync and return immediately."""
    try:
        ensure_refreshable_credentials(user)
    except ReauthenticationRequiredError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return _serialize_sync_status(await start_sync_job(user.id))


@router.get("/sync-status", response_model=SyncStatusOut)
async def get_channels_sync_status(
    user: User = Depends(get_current_user),
):
    return _serialize_sync_status(get_sync_status(user.id))


@router.delete("/{channel_id}")
async def remove_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a channel from user's subscriptions (local only)."""
    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == user.id,
            UserChannel.channel_id == channel_id,
        )
    )
    uc = result.scalar_one_or_none()
    if uc is None:
        raise HTTPException(status_code=404, detail="Channel not found in subscriptions")

    await db.delete(uc)
    await db.commit()
    return {"message": "Channel removed from subscriptions"}
