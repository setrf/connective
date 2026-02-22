import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.models.overlap_alert import OverlapAlert
from app.models.user import User
from app.schemas.notifications import (
    MarkReadRequest,
    NotificationsResponse,
    OverlapAlertOut,
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.get("", response_model=NotificationsResponse)
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List overlap alerts for the current user, newest first."""
    # Get alerts
    stmt = (
        select(OverlapAlert)
        .where(OverlapAlert.user_id == user.id)
        .order_by(OverlapAlert.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    # Get unread count
    count_stmt = (
        select(func.count())
        .select_from(OverlapAlert)
        .where(OverlapAlert.user_id == user.id, OverlapAlert.is_read == False)  # noqa: E712
    )
    unread_count = (await db.execute(count_stmt)).scalar() or 0

    # Resolve other user names
    alert_outs = []
    for alert in alerts:
        other_user_result = await db.execute(
            select(User).where(User.id == alert.other_user_id)
        )
        other_user = other_user_result.scalar_one_or_none()
        meta = alert.metadata_ or {}

        alert_outs.append(
            OverlapAlertOut(
                id=alert.id,
                summary=alert.summary,
                similarity_score=alert.similarity_score,
                is_read=alert.is_read,
                other_user_name=other_user.name if other_user else None,
                other_user_email=other_user.email if other_user else None,
                doc_a_title=meta.get("doc_a_title"),
                doc_a_provider=meta.get("doc_a_provider"),
                doc_a_url=meta.get("doc_a_url"),
                doc_b_title=meta.get("doc_b_title"),
                doc_b_provider=meta.get("doc_b_provider"),
                doc_b_url=meta.get("doc_b_url"),
                chat_message_id=alert.chat_message_id,
                created_at=alert.created_at,
            )
        )

    return NotificationsResponse(alerts=alert_outs, unread_count=unread_count)


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight endpoint for polling unread count."""
    stmt = (
        select(func.count())
        .select_from(OverlapAlert)
        .where(OverlapAlert.user_id == user.id, OverlapAlert.is_read == False)  # noqa: E712
    )
    count = (await db.execute(stmt)).scalar() or 0
    return {"unread_count": count}


@router.post("/mark-read")
async def mark_read(
    req: MarkReadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark specific alerts as read."""
    if not req.alert_ids:
        return {"status": "ok"}

    stmt = (
        select(OverlapAlert)
        .where(
            OverlapAlert.user_id == user.id,
            OverlapAlert.id.in_(req.alert_ids),
        )
    )
    result = await db.execute(stmt)
    for alert in result.scalars().all():
        alert.is_read = True
    await db.commit()
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all alerts as read for the current user."""
    stmt = (
        select(OverlapAlert)
        .where(
            OverlapAlert.user_id == user.id,
            OverlapAlert.is_read == False,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    for alert in result.scalars().all():
        alert.is_read = True
    await db.commit()
    return {"status": "ok"}
