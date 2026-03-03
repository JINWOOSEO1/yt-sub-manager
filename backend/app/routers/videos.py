from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth_utils import get_current_user
from app.database import get_db
from app.models import Channel, User, UserChannel, UserVideoState, Video
from app.schemas import (
    VideoDismissBatchRequest,
    VideoListResponse,
    VideoOut,
    VideoStatsOut,
)
from app.services.video_filters import is_short_video
from app.services.video_metadata import hydrate_video_metadata
from app.services.video_retention import get_video_cutoff

router = APIRouter()

VIDEO_SCAN_BATCH_SIZE = 40
VIDEO_SCAN_MAX_BATCHES = 3
VIDEO_HYDRATE_PER_BATCH = 40


@router.get("", response_model=VideoListResponse)
async def get_videos(
    status: str = Query("new", pattern="^(new|dismissed|watched|all)$"),
    channel_id: int | None = None,
    exclude_shorts: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get video feed for the current user."""
    cutoff = get_video_cutoff()

    # Base query: videos from user's subscribed channels
    base = (
        select(Video)
        .join(Channel, Video.channel_id == Channel.id)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(UserChannel.user_id == user.id)
        .where(Video.published_at >= cutoff)
        .options(joinedload(Video.channel))
    )

    # Join with user video state (LEFT JOIN)
    base = base.outerjoin(
        UserVideoState,
        and_(
            UserVideoState.video_id == Video.id,
            UserVideoState.user_id == user.id,
        ),
    )

    if status != "all":
        if status == "new":
            # Videos with no state or status='new'
            base = base.where(
                (UserVideoState.status == None) | (UserVideoState.status == "new")
            )
        else:
            base = base.where(UserVideoState.status == status)

    if channel_id is not None:
        base = base.where(Video.channel_id == channel_id)

    if exclude_shorts:
        start = (page - 1) * per_page
        end = start + per_page
        count_query = select(func.count()).select_from(base.subquery())
        raw_total = (await db.execute(count_query)).scalar() or 0

        filtered_videos: list[Video] = []
        scanned = 0
        batches = 0

        while len(filtered_videos) < end and batches < VIDEO_SCAN_MAX_BATCHES:
            query = (
                base.order_by(Video.published_at.desc())
                .offset(scanned)
                .limit(VIDEO_SCAN_BATCH_SIZE)
            )
            result = await db.execute(query)
            batch_videos = result.unique().scalars().all()
            if not batch_videos:
                break

            short_ids = await hydrate_video_metadata(
                db,
                user,
                batch_videos,
                delete_shorts=False,
                max_missing=VIDEO_HYDRATE_PER_BATCH,
            )
            filtered_videos.extend(
                video
                for video in batch_videos
                if video.id not in short_ids and not is_short_video(video.duration)
            )

            scanned += len(batch_videos)
            batches += 1

        videos = filtered_videos[start:end]
        total = len(filtered_videos) if scanned >= raw_total else raw_total
    else:
        count_query = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_query)).scalar() or 0
        query = (
            base.order_by(Video.published_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await db.execute(query)
        videos = result.unique().scalars().all()

    # Build response with status info
    video_ids = [v.id for v in videos]
    states_result = await db.execute(
        select(UserVideoState).where(
            UserVideoState.user_id == user.id,
            UserVideoState.video_id.in_(video_ids),
        )
    )
    state_map = {s.video_id: s.status for s in states_result.scalars().all()}

    items = []
    for v in videos:
        item = VideoOut.model_validate(v)
        item.status = state_map.get(v.id, "new")
        items.append(item)

    return VideoListResponse(items=items, total=total, page=page, per_page=per_page)


@router.patch("/{video_id}/dismiss")
async def dismiss_video(
    video_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a video (mark as not interested)."""
    await _set_video_status(db, user.id, video_id, "dismissed")
    return {"message": "Video dismissed"}


@router.patch("/{video_id}/watched")
async def mark_watched(
    video_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a video as watched."""
    await _set_video_status(db, user.id, video_id, "watched")
    return {"message": "Video marked as watched"}


@router.patch("/{video_id}/restore")
async def restore_video(
    video_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore a dismissed/watched video back to new status."""
    await _set_video_status(db, user.id, video_id, "new")
    return {"message": "Video restored"}


@router.post("/dismiss-batch")
async def dismiss_batch(
    body: VideoDismissBatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss multiple videos at once."""
    for vid in body.video_ids:
        await _set_video_status(db, user.id, vid, "dismissed")
    return {"message": f"Dismissed {len(body.video_ids)} videos"}


@router.get("/stats", response_model=VideoStatsOut)
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get video count statistics."""
    cutoff = get_video_cutoff()

    # Total videos from subscribed channels
    total_q = (
        select(func.count(Video.id))
        .join(Channel)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(UserChannel.user_id == user.id, Video.published_at >= cutoff)
    )
    total = (await db.execute(total_q)).scalar() or 0

    # Count by status
    status_q = (
        select(UserVideoState.status, func.count())
        .join(Video, Video.id == UserVideoState.video_id)
        .where(UserVideoState.user_id == user.id)
        .where(Video.published_at >= cutoff)
        .group_by(UserVideoState.status)
    )
    status_counts = {row[0]: row[1] for row in (await db.execute(status_q)).all()}

    dismissed = status_counts.get("dismissed", 0)
    watched = status_counts.get("watched", 0)
    new = total - dismissed - watched

    return VideoStatsOut(new=new, dismissed=dismissed, watched=watched, total=total)


async def _set_video_status(
    db: AsyncSession, user_id: int, video_id: int, status: str
):
    """Create or update a user's video state."""
    # Verify video exists AND belongs to a channel the user is subscribed to
    result = await db.execute(
        select(Video)
        .join(Channel, Video.channel_id == Channel.id)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(Video.id == video_id, UserChannel.user_id == user_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Video not found")

    result = await db.execute(
        select(UserVideoState).where(
            UserVideoState.user_id == user_id,
            UserVideoState.video_id == video_id,
        )
    )
    state = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if state is None:
        state = UserVideoState(
            user_id=user_id,
            video_id=video_id,
            status=status,
            dismissed_at=now if status == "dismissed" else None,
        )
        db.add(state)
    else:
        state.status = status
        if status == "dismissed":
            state.dismissed_at = now

    await db.commit()
