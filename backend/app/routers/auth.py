import logging
import os
import traceback
from datetime import datetime, timezone

# Allow Google to return a superset of requested scopes (e.g. userinfo.profile)
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from fastapi import APIRouter, Depends, HTTPException, Request
from google.auth.transport.requests import Request as GoogleRequest
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_utils import create_jwt, get_current_user
from app.config import settings
from app.database import get_db
from app.models import User, UserPreference
from app.schemas import FcmTokenRequest, GoogleAuthRequest, TokenResponse
from app.services.youtube_api import REAUTH_REQUIRED_DETAIL

logger = logging.getLogger(__name__)

router = APIRouter()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _should_require_reconsent(
    existing_refresh_token: str | None, new_refresh_token: str | None
) -> bool:
    return not existing_refresh_token and not new_refresh_token


@router.post("/google", response_model=TokenResponse)
@limiter.limit("10/minute")
async def google_auth(request: Request, body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google auth code for tokens and create/update user."""
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri="",  # Android requestServerAuthCode() uses empty redirect_uri
        )
        flow.fetch_token(code=body.auth_code)
        credentials = flow.credentials
    except Exception as e:
        logger.error("Auth code exchange failed: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Failed to exchange auth code: {e}")

    # Verify the ID token
    try:
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, GoogleRequest(), settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID token")

    google_sub = id_info["sub"]
    email = id_info.get("email")

    # Upsert user
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()
    existing_refresh_token = user.refresh_token if user is not None else None

    logger.info(
        "Google auth exchange completed for %s (has_new_refresh_token=%s, had_stored_refresh_token=%s)",
        email or google_sub,
        bool(credentials.refresh_token),
        bool(existing_refresh_token),
    )

    if _should_require_reconsent(existing_refresh_token, credentials.refresh_token):
        logger.warning(
            "Rejecting Google login for %s because no refresh token is available after auth exchange",
            email or google_sub,
        )
        raise HTTPException(status_code=400, detail=REAUTH_REQUIRED_DETAIL)

    if user is None:
        user = User(
            google_sub=google_sub,
            email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expires_at=credentials.expiry,
        )
        db.add(user)
        await db.flush()
        # Create default preferences
        db.add(UserPreference(user_id=user.id))
    else:
        user.access_token = credentials.token
        if credentials.refresh_token:
            user.refresh_token = credentials.refresh_token
        user.token_expires_at = credentials.expiry

    await db.commit()

    logger.info(
        "Stored Google credentials for user %d (has_refresh_token=%s)",
        user.id,
        bool(user.refresh_token),
    )

    jwt_token = create_jwt(user.id)
    return TokenResponse(access_token=jwt_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh the JWT token. Requires valid current JWT in header."""
    jwt_token = create_jwt(user.id)
    return TokenResponse(access_token=jwt_token)


@router.post("/fcm-token")
async def register_fcm_token(
    body: FcmTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register or update the FCM token for push notifications."""
    user.fcm_token = body.fcm_token
    await db.commit()
    return {"message": "FCM token registered"}


@router.delete("/logout")
async def logout():
    """Logout - client should discard the JWT."""
    return {"message": "Logged out successfully"}
