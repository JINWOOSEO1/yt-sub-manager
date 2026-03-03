"""YouTube Data API v3 client wrapper."""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

from app.config import settings
from app.models import User

logger = logging.getLogger(__name__)

_PLAYER_RESPONSE_RE = re.compile(r"ytInitialPlayerResponse\s*=\s*({.+?});", re.DOTALL)
_PUBLISHED_TIME_RE = re.compile(r'"publishDate":"([^"]+)"')
REAUTH_REQUIRED_DETAIL = (
    "Google offline access is missing. Sign out, remove this app from your "
    "Google account's third-party access, then sign in again."
)


class ReauthenticationRequiredError(RuntimeError):
    """Raised when stored Google credentials cannot be refreshed."""


def _get_credentials(user: User) -> Credentials:
    """Build Google credentials from stored user tokens."""
    creds = Credentials(
        token=user.access_token,
        refresh_token=user.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        expiry=user.token_expires_at,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
    return creds


def _build_service(user: User):
    """Build the YouTube API service client."""
    from googleapiclient.discovery import build

    creds = _get_credentials(user)
    return build("youtube", "v3", credentials=creds)


def _has_refreshable_credentials(user: User) -> bool:
    return bool(
        user.access_token
        and user.refresh_token
        and settings.google_client_id
        and settings.google_client_secret
    )


def ensure_refreshable_credentials(user: User):
    if _has_refreshable_credentials(user):
        return

    raise ReauthenticationRequiredError(REAUTH_REQUIRED_DETAIL)


async def fetch_subscriptions(user: User) -> list[dict]:
    """Fetch all subscriptions for a user. Returns list of channel info dicts."""
    ensure_refreshable_credentials(user)

    try:
        service = _build_service(user)
    except Exception:
        logger.exception("Failed to build YouTube API service for user %d", user.id)
        raise

    channels = []
    page_token = None

    try:
        while True:
            request = service.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=page_token,
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]
                channels.append(
                    {
                        "youtube_channel_id": snippet["resourceId"]["channelId"],
                        "title": snippet["title"],
                        "thumbnail_url": snippet["thumbnails"]
                        .get("default", {})
                        .get("url"),
                    }
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break
    except Exception:
        logger.exception(
            "Failed to fetch subscriptions for user %d (got %d so far)",
            user.id,
            len(channels),
        )
        raise

    logger.info(
        "Fetched %d subscriptions for user %d",
        len(channels),
        user.id,
    )

    return channels


async def fetch_video_details(user: User, video_ids: list[str]) -> list[dict]:
    """Fetch video details by IDs, preferring YouTube API and falling back to public pages."""
    if not video_ids:
        return []

    results = []
    fetched_ids: set[str] = set()

    if _has_refreshable_credentials(user):
        try:
            service = _build_service(user)
            for idx in range(0, len(video_ids), 50):
                chunk = video_ids[idx : idx + 50]
                request = service.videos().list(
                    part="snippet,contentDetails",
                    id=",".join(chunk),
                    maxResults=len(chunk),
                )
                data = request.execute()

                for item in data.get("items", []):
                    snippet = item["snippet"]
                    results.append(
                        {
                            "youtube_video_id": item["id"],
                            "title": snippet["title"],
                            "thumbnail_url": snippet["thumbnails"]
                            .get("medium", snippet["thumbnails"].get("default", {}))
                            .get("url"),
                            "published_at": datetime.fromisoformat(
                                snippet["publishedAt"].replace("Z", "+00:00")
                            ),
                            "channel_id_yt": snippet["channelId"],
                            "duration": item.get("contentDetails", {}).get("duration"),
                        }
                    )
                    fetched_ids.add(item["id"])
        except Exception:
            logger.exception("Unexpected error fetching video details from YouTube API")
    else:
        logger.warning(
            "Skipping YouTube API video details fetch for user %d because refresh credentials are incomplete; reauthentication is required",
            user.id,
        )

    remaining_ids = [video_id for video_id in video_ids if video_id not in fetched_ids]
    if remaining_ids:
        results.extend(await _fetch_video_details_from_web(remaining_ids))

    return results


async def _fetch_video_details_from_web(video_ids: list[str]) -> list[dict]:
    """Best-effort public fallback for video duration/title metadata."""
    semaphore = asyncio.Semaphore(8)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        tasks = [
            _fetch_single_video_detail_from_web(client, video_id, semaphore)
            for video_id in video_ids
        ]
        results = await asyncio.gather(*tasks)

    return [item for item in results if item]


async def _fetch_single_video_detail_from_web(
    client: httpx.AsyncClient, video_id: str, semaphore: asyncio.Semaphore
) -> dict | None:
    async with semaphore:
        try:
            resp = await client.get(f"https://www.youtube.com/watch?v={video_id}")
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch public video page for %s", video_id)
            return None

        player_response = _extract_player_response(resp.text)
        if not player_response:
            logger.warning("Could not parse player response for %s", video_id)
            return None

        details = player_response.get("videoDetails", {})
        microformat = (
            player_response.get("microformat", {}).get("playerMicroformatRenderer", {})
        )

        length_seconds = details.get("lengthSeconds")
        duration = None
        if length_seconds is not None:
            duration = _seconds_to_iso8601_duration(int(length_seconds))

        published_at = _parse_published_at(
            microformat.get("publishDate") or _extract_publish_date(resp.text)
        )

        thumbnail_url = None
        thumbnails = details.get("thumbnail", {}).get("thumbnails", [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get("url")

        return {
            "youtube_video_id": video_id,
            "title": details.get("title"),
            "thumbnail_url": thumbnail_url,
            "published_at": published_at,
            "channel_id_yt": details.get("channelId"),
            "duration": duration,
        }


def _extract_player_response(html: str) -> dict | None:
    match = _PLAYER_RESPONSE_RE.search(html)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_publish_date(html: str) -> str | None:
    match = _PUBLISHED_TIME_RE.search(html)
    return match.group(1) if match else None


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        if "T" in normalized:
            return datetime.fromisoformat(normalized)
        return datetime.fromisoformat(f"{normalized}T00:00:00+00:00")
    except ValueError:
        logger.warning("Could not parse published_at value: %s", value)
        return None


def _seconds_to_iso8601_duration(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration = "PT"
    if hours:
        duration += f"{hours}H"
    if minutes:
        duration += f"{minutes}M"
    if seconds or duration == "PT":
        duration += f"{seconds}S"
    return duration
