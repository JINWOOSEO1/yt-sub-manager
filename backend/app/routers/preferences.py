from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_utils import get_current_user
from app.database import get_db
from app.models import User, UserPreference
from app.schemas import PreferencesOut, PreferencesUpdate
from app.services.video_retention import RECENT_VIDEO_WINDOW_DAYS

router = APIRouter()


@router.get("", response_model=PreferencesOut)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user preferences."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        # Create default preferences
        pref = UserPreference(user_id=user.id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    elif pref.auto_delete_days > RECENT_VIDEO_WINDOW_DAYS:
        pref.auto_delete_days = RECENT_VIDEO_WINDOW_DAYS
        await db.commit()
        await db.refresh(pref)
    return pref


@router.put("", response_model=PreferencesOut)
async def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user preferences."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = UserPreference(user_id=user.id)
        db.add(pref)

    update_data = body.model_dump(exclude_unset=True)
    if "auto_delete_days" in update_data and update_data["auto_delete_days"] is not None:
        update_data["auto_delete_days"] = min(
            update_data["auto_delete_days"], RECENT_VIDEO_WINDOW_DAYS
        )
    for key, value in update_data.items():
        setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)
    return pref
