from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_sub: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    fcm_token: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    channels: Mapped[list["Channel"]] = relationship(
        secondary="user_channels", back_populates="users"
    )
    video_states: Mapped[list["UserVideoState"]] = relationship(back_populates="user")
    preferences: Mapped["UserPreference | None"] = relationship(back_populates="user")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    youtube_channel_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    websub_active: Mapped[bool] = mapped_column(Boolean, default=False)
    websub_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    users: Mapped[list["User"]] = relationship(
        secondary="user_channels", back_populates="channels"
    )
    videos: Mapped[list["Video"]] = relationship(back_populates="channel")


class UserChannel(Base):
    __tablename__ = "user_channels"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True
    )


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        Index("idx_videos_channel", "channel_id"),
        Index("idx_videos_published", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    youtube_video_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration: Mapped[str | None] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    channel: Mapped["Channel"] = relationship(back_populates="videos")
    user_states: Mapped[list["UserVideoState"]] = relationship(back_populates="video")


class UserVideoState(Base):
    __tablename__ = "user_video_states"
    __table_args__ = (Index("idx_user_video_status", "user_id", "status"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="video_states")
    video: Mapped["Video"] = relationship(back_populates="user_states")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    auto_delete_days: Mapped[int] = mapped_column(Integer, default=14)
    polling_interval_min: Mapped[int] = mapped_column(Integer, default=15)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="preferences")
