from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _to_out(db: Session, user: models.User) -> schemas.UserProfileOut:
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
    active = (
        db.query(models.Issue)
        .filter(
            models.Issue.assignee_id == user.id,
            models.Issue.status.in_([models.Status.open, models.Status.in_progress]),
        )
        .count()
    )
    resolved = (
        db.query(models.Issue)
        .filter(
            models.Issue.assignee_id == user.id,
            models.Issue.status.in_([models.Status.resolved, models.Status.closed]),
        )
        .count()
    )
    return schemas.UserProfileOut(
        user_id=user.id,
        username=user.username,
        skills=profile.skills if profile else [],
        specialization=profile.specialization if profile else "",
        experience_years=profile.experience_years if profile else 0,
        bio=profile.bio if profile else "",
        active_issue_count=active,
        resolved_issue_count=resolved,
    )


@router.get("", response_model=list[schemas.UserProfileOut])
def list_profiles(db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    users = db.query(models.User).all()
    return [_to_out(db, u) for u in users]


@router.get("/me", response_model=schemas.UserProfileOut)
def my_profile(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return _to_out(db, current_user)


@router.patch("/me", response_model=schemas.UserProfileOut)
def update_my_profile(
    payload: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = models.UserProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    return _to_out(db, current_user)
