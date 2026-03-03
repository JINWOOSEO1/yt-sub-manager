import os

import pytest

os.environ.setdefault("YSM_JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("YSM_WEBSUB_SECRET", "test-websub-secret")
os.environ.setdefault("YSM_GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("YSM_GOOGLE_CLIENT_SECRET", "test-client-secret")

from app.models import User
from app.routers.auth import _should_require_reconsent
from app.services.youtube_api import (
    REAUTH_REQUIRED_DETAIL,
    ReauthenticationRequiredError,
    ensure_refreshable_credentials,
)


def test_should_require_reconsent_without_existing_or_new_refresh_token():
    assert _should_require_reconsent(None, None)


def test_should_not_require_reconsent_with_existing_refresh_token():
    assert not _should_require_reconsent("stored-refresh-token", None)


def test_should_not_require_reconsent_with_new_refresh_token():
    assert not _should_require_reconsent(None, "new-refresh-token")


def test_ensure_refreshable_credentials_raises_actionable_error():
    user = User(
        id=1,
        google_sub="sub-1",
        email="user@example.com",
        access_token="access-token",
        refresh_token=None,
    )

    with pytest.raises(ReauthenticationRequiredError) as exc_info:
        ensure_refreshable_credentials(user)

    assert str(exc_info.value) == REAUTH_REQUIRED_DETAIL


def test_ensure_refreshable_credentials_accepts_complete_credentials():
    user = User(
        id=1,
        google_sub="sub-1",
        email="user@example.com",
        access_token="access-token",
        refresh_token="refresh-token",
    )

    ensure_refreshable_credentials(user)
