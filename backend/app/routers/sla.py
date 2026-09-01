from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/sla", tags=["sla"])


@router.get("/policies", response_model=list[schemas.SLAPolicyOut])
def list_policies(project_id: Optional[int] = None, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    q = db.query(models.SLAPolicy)
    if project_id:
        q = q.filter(models.SLAPolicy.project_id == project_id)
    return q.all()


@router.post("/policies", response_model=schemas.SLAPolicyOut)
def create_policy(payload: schemas.SLAPolicyCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    policy = models.SLAPolicy(
        project_id=payload.project_id,
        name=payload.name,
        priority=payload.priority,
        resolution_hours=payload.resolution_hours,
        escalate_to_role=payload.escalate_to_role,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/policies/{policy_id}")
def delete_policy(policy_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_admin)):
    policy = db.query(models.SLAPolicy).filter(models.SLAPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.commit()
    return {"ok": True}


@router.get("/breaches")
def list_breaches(project_id: Optional[int] = None, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    policies_q = db.query(models.SLAPolicy)
    if project_id:
        policies_q = policies_q.filter(models.SLAPolicy.project_id == project_id)
    policies = {p.priority: p for p in policies_q.all()}

    if not policies:
        return []

    issues_q = db.query(models.Issue).filter(
        models.Issue.status.notin_([models.Status.resolved, models.Status.closed])
    )
    if project_id:
        issues_q = issues_q.filter(models.Issue.project_id == project_id)

    breaches = []
    now = datetime.utcnow()
    for issue in issues_q.all():
        policy = policies.get(issue.priority)
        if not policy:
            continue
        deadline = issue.created_at + timedelta(hours=policy.resolution_hours)
        if now > deadline:
            breaches.append({
                "issue_id": issue.id,
                "number": issue.number,
                "title": issue.title,
                "priority": issue.priority.value,
                "policy_name": policy.name,
                "hours_overdue": round((now - deadline).total_seconds() / 3600, 1),
                "escalate_to_role": policy.escalate_to_role,
            })
    return breaches
