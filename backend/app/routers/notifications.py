from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.Notification).filter(models.Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(models.Notification.is_read == 0)
    return q.order_by(models.Notification.created_at.desc()).limit(50).all()


@router.patch("/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    n = db.query(models.Notification).filter(
        models.Notification.id == notif_id, models.Notification.user_id == current_user.id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = 1
    db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id, models.Notification.is_read == 0
    ).update({models.Notification.is_read: 1})
    db.commit()
    return {"ok": True}
