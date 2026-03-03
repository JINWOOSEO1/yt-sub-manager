# YouTube Subscription Manager

YouTube Subscription Manager is an Android app with a FastAPI backend for organizing and managing new videos from your subscribed YouTube channels in one place.

Instead of relying on the default YouTube subscription feed, the app is designed more like a personal inbox for videos you actually want to watch. After signing in with a Google account, users can sync their subscriptions, browse recent uploads by channel, and quickly clear out videos they are not interested in.

## Key Features

- Sign in with Google and connect your YouTube subscriptions
- Browse recent videos from subscribed channels
- Filter videos by channel
- Dismiss videos you do not want to watch
- Undo accidental dismiss actions
- Exclude Shorts from the feed
- Configure new video notifications
- Set automatic cleanup rules for older videos
- Detect new uploads through WebSub and periodic polling

## Project Structure

### Android App

- Jetpack Compose-based UI
- Google Sign-In authentication
- Feed, channel filter, and settings screens
- Firebase Cloud Messaging (FCM) integration

### Backend API

- FastAPI-based REST API
- SQLite with SQLAlchemy
- Subscription sync and per-user video state management
- APScheduler jobs for polling, WebSub renewal, and cleanup

## User Flow

1. Sign in with a Google account.
2. Sync subscribed channels.
3. Review newly uploaded videos.
4. Filter by channel or dismiss videos you do not want to keep.
5. Adjust notifications, polling interval, and cleanup settings.

## Tech Stack

- Android: Kotlin, Jetpack Compose, Hilt, Retrofit, DataStore, Firebase Messaging
- Backend: Python, FastAPI, SQLAlchemy, Alembic, APScheduler
- External Services: Google OAuth, YouTube data access, WebSub, Firebase Cloud Messaging

## Local Development

### 1. Run the Backend

Set the following environment variables in `backend/.env`:

- `YSM_JWT_SECRET_KEY`
- `YSM_WEBSUB_SECRET`
- `YSM_GOOGLE_CLIENT_ID`
- `YSM_GOOGLE_CLIENT_SECRET`
- `YSM_FIREBASE_CREDENTIALS_PATH` (optional)

Example:

```bash
cd backend
pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use:

```bash
./scripts/run_dev.sh
```

The default SQLite database is created at `backend/data/youtube_sub_manager.db`.

### 2. Run the Android App

- Open the `android/` project in Android Studio.
- Check `BASE_URL` in `android/app/build.gradle.kts` and make sure it matches your backend environment.
- Prepare Google Sign-In and Firebase configuration files, then run the app.

## Health Check

When the backend is running, you can verify its status with:

```text
GET /health
```

## License

See [LICENSE](LICENSE).
