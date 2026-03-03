from datetime import datetime

from pydantic import BaseModel, Field


# --- Auth ---
class GoogleAuthRequest(BaseModel):
    auth_code: str = Field(min_length=1)


class FcmTokenRequest(BaseModel):
    fcm_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SyncStatusOut(BaseModel):
    state: str
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    channel_count: int | None = None
    error: str | None = None


# --- Channel ---
class ChannelOut(BaseModel):
    id: int
    youtube_channel_id: str
    title: str
    thumbnail_url: str | None

    model_config = {"from_attributes": True}


# --- Video ---
class VideoOut(BaseModel):
    id: int
    youtube_video_id: str
    title: str
    thumbnail_url: str | None
    published_at: datetime
    duration: str | None
    status: str = "new"
    channel: ChannelOut

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoOut]
    total: int
    page: int
    per_page: int


class VideoDismissBatchRequest(BaseModel):
    video_ids: list[int] = Field(min_length=1, max_length=100)


class VideoStatsOut(BaseModel):
    new: int
    dismissed: int
    watched: int
    total: int


# --- Preferences ---
class PreferencesOut(BaseModel):
    auto_delete_days: int
    polling_interval_min: int
    notification_enabled: bool

    model_config = {"from_attributes": True}


class PreferencesUpdate(BaseModel):
    auto_delete_days: int | None = None
    polling_interval_min: int | None = None
    notification_enabled: bool | None = None
