"""Firebase Cloud Messaging service for sending push notifications."""

import logging

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Channel, User, UserChannel, UserPreference

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _init_firebase():
    """Initialize Firebase Admin SDK (once)."""
    global _firebase_initialized
    if _firebase_initialized:
        return True
    if not settings.firebase_credentials_path:
        logger.warning("Firebase credentials path not set, FCM disabled")
        return False
    try:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized")
        return True
    except Exception:
        logger.exception("Failed to initialize Firebase Admin SDK")
        return False


async def send_new_video_notification(
    db: AsyncSession, channel: Channel, video_title: str
):
    """Send FCM push notification to all users subscribed to this channel."""
    if not _init_firebase():
        return

    # Find all users subscribed to this channel with notifications enabled
    result = await db.execute(
        select(User)
        .join(UserChannel, UserChannel.user_id == User.id)
        .outerjoin(UserPreference, UserPreference.user_id == User.id)
        .where(
            UserChannel.channel_id == channel.id,
            User.fcm_token.isnot(None),
            (UserPreference.notification_enabled == True)  # noqa: E712
            | (UserPreference.user_id == None),  # default is enabled
        )
    )
    users = result.unique().scalars().all()

    if not users:
        return

    for user in users:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"{channel.title}",
                    body=video_title,
                ),
                token=user.fcm_token,
                data={
                    "type": "new_video",
                    "channel_title": channel.title,
                    "video_title": video_title,
                },
            )
            messaging.send(message)
            logger.info("FCM sent to user %d for channel %s", user.id, channel.title)
        except messaging.UnregisteredError:
            # Token is invalid, clear it
            user.fcm_token = None
            logger.info("Cleared invalid FCM token for user %d", user.id)
        except Exception:
            logger.exception("Failed to send FCM to user %d", user.id)

    await db.commit()
