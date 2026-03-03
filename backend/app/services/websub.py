"""WebSub (PubSubHubbub) subscription manager for YouTube push notifications."""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Channel

logger = logging.getLogger(__name__)

HUB_URL = "https://pubsubhubbub.appspot.com/subscribe"
TOPIC_URL_TEMPLATE = (
    "https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"
)
LEASE_SECONDS = 432000  # 5 days


async def subscribe_channel(channel_id: str) -> bool:
    """Subscribe to WebSub push notifications for a YouTube channel.

    Returns True if the subscription request was sent successfully.
    """
    topic_url = TOPIC_URL_TEMPLATE.format(channel_id=channel_id)
    callback_url = settings.websub_callback_url

    data = {
        "hub.callback": callback_url,
        "hub.topic": topic_url,
        "hub.verify": "async",
        "hub.mode": "subscribe",
        "hub.lease_seconds": str(LEASE_SECONDS),
        "hub.secret": settings.websub_secret,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(HUB_URL, data=data)
            # 202 Accepted means the hub will verify the callback asynchronously
            if resp.status_code == 202:
                logger.info("WebSub subscribe request sent for channel %s", channel_id)
                return True
            logger.warning(
                "WebSub subscribe failed for %s: %s %s",
                channel_id,
                resp.status_code,
                resp.text,
            )
            return False
        except Exception:
            logger.exception("WebSub subscribe error for channel %s", channel_id)
            return False


async def unsubscribe_channel(channel_id: str) -> bool:
    """Unsubscribe from WebSub for a YouTube channel."""
    topic_url = TOPIC_URL_TEMPLATE.format(channel_id=channel_id)

    data = {
        "hub.callback": settings.websub_callback_url,
        "hub.topic": topic_url,
        "hub.mode": "unsubscribe",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(HUB_URL, data=data)
            return resp.status_code == 202
        except Exception:
            logger.exception("WebSub unsubscribe error for channel %s", channel_id)
            return False


def verify_signature(body: bytes, signature: str) -> bool:
    """Verify the HMAC-SHA1 signature from the hub."""
    if not signature.startswith("sha1="):
        return False
    expected = hmac.new(
        settings.websub_secret.encode(), body, hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(expected, signature[5:])


async def subscribe_all_channels(db: AsyncSession):
    """Subscribe all channels to WebSub. Called by scheduler."""
    result = await db.execute(select(Channel))
    channels = result.scalars().all()

    for channel in channels:
        success = await subscribe_channel(channel.youtube_channel_id)
        if success:
            channel.websub_active = True
            from datetime import timedelta

            channel.websub_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=LEASE_SECONDS
            )

    await db.commit()
    logger.info("WebSub subscription renewal completed for %d channels", len(channels))
