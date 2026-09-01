from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


def _to_out(m: models.Milestone, db: Session) -> schemas.MilestoneOut:
    total = db.query(models.Issue).filter(models.Issue.milestone_id == m.id).count()
    done = (
        db.query(models.Issue)
        .filter(
            models.Issue.milestone_id == m.id,
            models.Issue.status.in_([models.Status.resolved, models.Status.closed]),
        )
        .count()
    )
    return schemas.MilestoneOut(
        id=m.id, project_id=m.project_id, title=m.title, description=m.description,
        due_date=m.due_date, status=m.status, created_at=m.created_at,
        issue_count=total, done_count=done,
    )


@router.get("", response_model=list[schemas.MilestoneOut])
def list_milestones(project_id: Optional[int] = None, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    q = db.query(models.Milestone)
    if project_id:
        q = q.filter(models.Milestone.project_id == project_id)
    milestones = q.order_by(models.Milestone.due_date.is_(None), models.Milestone.due_date.asc()).all()
    return [_to_out(m, db) for m in milestones]


@router.post("", response_model=schemas.MilestoneOut)
def create_milestone(payload: schemas.MilestoneCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    m = models.Milestone(
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _to_out(m, db)


@router.patch("/{milestone_id}", response_model=schemas.MilestoneOut)
def update_milestone(milestone_id: int, payload: schemas.MilestoneUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    m = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(m, field, value)
    db.commit()
    db.refresh(m)
    return _to_out(m, db)


@router.delete("/{milestone_id}")
def delete_milestone(milestone_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    m = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    db.query(models.Issue).filter(models.Issue.milestone_id == milestone_id).update({models.Issue.milestone_id: None})
    db.delete(m)
    db.commit()
    return {"ok": True}
