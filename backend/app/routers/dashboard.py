from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, auth
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    q = db.query(models.Issue)
    if project_id:
        q = q.filter(models.Issue.project_id == project_id)

    total = q.count()

    by_status = dict(
        db.query(models.Issue.status, func.count(models.Issue.id))
        .filter(models.Issue.project_id == project_id if project_id else True)
        .group_by(models.Issue.status)
        .all()
    )
    by_priority = dict(
        db.query(models.Issue.priority, func.count(models.Issue.id))
        .filter(models.Issue.project_id == project_id if project_id else True)
        .group_by(models.Issue.priority)
        .all()
    )
    by_type = dict(
        db.query(models.Issue.issue_type, func.count(models.Issue.id))
        .filter(models.Issue.project_id == project_id if project_id else True)
        .group_by(models.Issue.issue_type)
        .all()
    )

    overdue_q = db.query(models.Issue).filter(
        models.Issue.due_date != None,
        models.Issue.due_date < datetime.utcnow(),
        models.Issue.status.notin_([models.Status.resolved, models.Status.closed]),
    )
    if project_id:
        overdue_q = overdue_q.filter(models.Issue.project_id == project_id)
    overdue_count = overdue_q.count()

    return {
        "total": total,
        "by_status": {k.value: v for k, v in by_status.items()},
        "by_priority": {k.value: v for k, v in by_priority.items()},
        "by_type": {k.value: v for k, v in by_type.items()},
        "overdue_count": overdue_count,
    }


@router.get("/workload")
def workload(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    users = db.query(models.User).all()
    result = []
    for u in users:
        q = db.query(models.Issue).filter(models.Issue.assignee_id == u.id)
        if project_id:
            q = q.filter(models.Issue.project_id == project_id)
        open_count = q.filter(models.Issue.status == models.Status.open).count()
        in_progress_count = q.filter(models.Issue.status == models.Status.in_progress).count()
        total = q.count()
        result.append({
            "user_id": u.id,
            "username": u.username,
            "open_count": open_count,
            "in_progress_count": in_progress_count,
            "total_count": total,
        })
    result.sort(key=lambda r: -(r["open_count"] + r["in_progress_count"]))
    return result


