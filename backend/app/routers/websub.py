"""WebSub callback endpoint for receiving YouTube push notifications."""

import logging
from datetime import datetime, timezone

from defusedxml import ElementTree
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Channel, Video
from app.services.video_retention import get_video_cutoff
from app.services.websub import verify_signature

logger = logging.getLogger(__name__)

router = APIRouter()

ATOM_NS = "http://www.w3.org/2005/Atom"
YT_NS = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"


@router.get("/callback")
async def websub_verify(
    hub_topic: str = Query(alias="hub.topic"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_mode: str = Query(alias="hub.mode"),
    hub_lease_seconds: int | None = Query(None, alias="hub.lease_seconds"),
):
    """Handle WebSub subscription verification from the hub."""
    logger.info("WebSub verification: mode=%s topic=%s", hub_mode, hub_topic)
    # Return the challenge to confirm the subscription
    return Response(content=hub_challenge, media_type="text/plain")


@router.post("/callback")
async def websub_notification(
    request: Request,
    x_hub_signature: str | None = Header(None),
):
    """Handle WebSub push notification (new video uploaded)."""
    body = await request.body()

    # Verify HMAC signature (mandatory)
    if not x_hub_signature:
        logger.warning("WebSub notification rejected: missing signature")
        raise HTTPException(status_code=403, detail="Missing signature")
    if not verify_signature(body, x_hub_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse Atom XML
    try:
        root = ElementTree.fromstring(body)
    except Exception:
        logger.exception("Failed to parse WebSub notification XML")
        raise HTTPException(status_code=400, detail="Invalid XML")

    # Process entries
    async with async_session() as db:
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            await _process_entry(db, entry)
        await db.commit()

    return Response(status_code=204)


async def _process_entry(db: AsyncSession, entry):
    """Process a single Atom entry from a WebSub notification."""
    video_id_el = entry.find(f"{{{YT_NS}}}videoId")
    channel_id_el = entry.find(f"{{{YT_NS}}}channelId")

    if video_id_el is None or channel_id_el is None:
        return

    video_id = video_id_el.text
    channel_yt_id = channel_id_el.text

    # Check if video already exists
    result = await db.execute(
        select(Video).where(Video.youtube_video_id == video_id)
    )
    if result.scalar_one_or_none() is not None:
        return  # Already known

    # Find the channel in our DB
    result = await db.execute(
        select(Channel).where(Channel.youtube_channel_id == channel_yt_id)
    )
    channel = result.scalar_one_or_none()
    if channel is None:
        logger.warning("Received notification for unknown channel: %s", channel_yt_id)
        return

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
    if published_at < get_video_cutoff():
        return

    video = Video(
        youtube_video_id=video_id,
        channel_id=channel.id,
        title=title_el.text if title_el is not None else "Unknown",
        thumbnail_url=thumbnail_url,
        published_at=published_at,
    )
    db.add(video)
    await db.flush()
    logger.info("New video from WebSub: %s - %s", video_id, video.title)

    # Send FCM push notification to subscribed users
    from app.services.fcm import send_new_video_notification

    await send_new_video_notification(db, channel, video.title)
