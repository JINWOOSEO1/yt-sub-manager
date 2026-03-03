import os
from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects import sqlite

os.environ.setdefault("YSM_JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("YSM_WEBSUB_SECRET", "test-websub-secret")

from app.models import User, Video
from app.services.video_metadata import hydrate_video_metadata


class RecordingSession:
    def __init__(self):
        self.statements = []
        self.commits = 0

    async def execute(self, statement):
        self.statements.append(statement)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_hydrate_video_metadata_deletes_states_before_short_videos():
    session = RecordingSession()
    user = User(id=1, google_sub="sub-1")
    video = Video(
        id=42,
        youtube_video_id="video-1",
        title="Short clip",
        published_at=datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc),
        duration="PT59S",
    )

    short_ids = await hydrate_video_metadata(session, user, [video])

    assert short_ids == {42}
    assert session.commits == 1
    assert len(session.statements) == 2

    compiled = [
        str(
            statement.compile(
                dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        for statement in session.statements
    ]

    assert compiled[0] == "DELETE FROM user_video_states WHERE user_video_states.video_id IN (42)"
    assert compiled[1] == "DELETE FROM videos WHERE videos.id IN (42)"
