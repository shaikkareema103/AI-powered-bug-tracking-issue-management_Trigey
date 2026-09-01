from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/sprints", tags=["sprints"])


def _to_out(s: models.Sprint, db: Session) -> schemas.SprintOut:
    total = db.query(models.Issue).filter(models.Issue.sprint_id == s.id).count()
    done = (
        db.query(models.Issue)
        .filter(
            models.Issue.sprint_id == s.id,
            models.Issue.status.in_([models.Status.resolved, models.Status.closed]),
        )
        .count()
    )
    return schemas.SprintOut(
        id=s.id, project_id=s.project_id, name=s.name, goal=s.goal,
        start_date=s.start_date, end_date=s.end_date, status=s.status,
        created_at=s.created_at, issue_count=total, done_count=done,
    )


@router.get("", response_model=list[schemas.SprintOut])
def list_sprints(project_id: Optional[int] = None, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    q = db.query(models.Sprint)
    if project_id:
        q = q.filter(models.Sprint.project_id == project_id)
    sprints = q.order_by(models.Sprint.start_date.is_(None), models.Sprint.start_date.desc()).all()
    return [_to_out(s, db) for s in sprints]


@router.post("", response_model=schemas.SprintOut)
def create_sprint(payload: schemas.SprintCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    s = models.Sprint(
        project_id=payload.project_id,
        name=payload.name,
        goal=payload.goal,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_out(s, db)


@router.patch("/{sprint_id}", response_model=schemas.SprintOut)
def update_sprint(sprint_id: int, payload: schemas.SprintUpdate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    s = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sprint not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return _to_out(s, db)


@router.delete("/{sprint_id}")
def delete_sprint(sprint_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    s = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sprint not found")
    db.query(models.Issue).filter(models.Issue.sprint_id == sprint_id).update({models.Issue.sprint_id: None})
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/{sprint_id}/risk")
def sprint_risk(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    from datetime import datetime
    from .. import ai_service

    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    issues = db.query(models.Issue).filter(models.Issue.sprint_id == sprint_id).all()
    total = len(issues)
    resolved = len([i for i in issues if i.status in (models.Status.resolved, models.Status.closed)])
    open_issues = [i for i in issues if i.status not in (models.Status.resolved, models.Status.closed)]

    if sprint.end_date:
        days_remaining = max(0, (sprint.end_date - datetime.utcnow()).days)
    else:
        days_remaining = "unknown (no end date set)"

    open_summary = [
        {"title": i.title, "priority": i.priority.value, "status": i.status.value}
        for i in open_issues[:20]
    ]

    try:
        result = ai_service.analyze_sprint_risk(
            sprint.name, sprint.goal, days_remaining, total, resolved, open_summary
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI risk analysis failed: {e}")

    return result


@router.post("/{sprint_id}/copilot")
def sprint_copilot(
    sprint_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    from .. import ai_service

    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    issues = db.query(models.Issue).filter(models.Issue.sprint_id == sprint_id).all()
    issues_lines = "\n".join(
        f'- #{i.number} "{i.title}" [{i.priority.value}, {i.status.value}]'
        + (f' assigned to {i.assignee.username}' if i.assignee else ' unassigned')
        for i in issues
    ) or "(no issues in this sprint)"

    context = f"""Sprint: {sprint.name}
Goal: {sprint.goal or "(none set)"}
Status: {sprint.status.value}
Start: {sprint.start_date}
End: {sprint.end_date}

Issues in this sprint:
{issues_lines}"""

    question = payload.get("question", "")
    chat_history = payload.get("history", [])

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    try:
        answer = ai_service.sprint_copilot_chat(context, chat_history, question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Copilot failed: {e}")

    return {"answer": answer}


@router.post("/{sprint_id}/plan")
def plan_sprint_endpoint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    from .. import ai_service

    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    backlog = (
        db.query(models.Issue)
        .filter(
            models.Issue.project_id == sprint.project_id,
            models.Issue.sprint_id == None,
            models.Issue.status.notin_([models.Status.resolved, models.Status.closed]),
        )
        .limit(30)
        .all()
    )

    if not backlog:
        return {"selected_issue_ids": [], "reasoning": "No unassigned backlog issues available."}

    backlog_data = [
        {"id": i.id, "number": i.number, "title": i.title, "priority": i.priority.value}
        for i in backlog
    ]

    try:
        result = ai_service.plan_sprint(sprint.name, sprint.goal, "typical small-team sprint capacity", backlog_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sprint planning failed: {e}")

    return result


@router.post("/{sprint_id}/plan/apply")
def apply_sprint_plan(
    sprint_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    issue_ids = payload.get("issue_ids", [])
    db.query(models.Issue).filter(models.Issue.id.in_(issue_ids)).update(
        {models.Issue.sprint_id: sprint_id}, synchronize_session=False
    )
    db.commit()
    return {"ok": True, "count": len(issue_ids)}
