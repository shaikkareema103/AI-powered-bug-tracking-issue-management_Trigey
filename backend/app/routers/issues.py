import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas, auth, ai_service
from ..database import get_db

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("", response_model=list[schemas.IssueOut])
def list_issues(
    project_id: Optional[int] = None,
    status: Optional[models.Status] = None,
    priority: Optional[models.Priority] = None,
    assignee_id: Optional[int] = None,
    milestone_id: Optional[int] = None,
    sprint_id: Optional[int] = None,
    search: Optional[str] = None,
    overdue_only: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    q = db.query(models.Issue)
    if project_id:
        q = q.filter(models.Issue.project_id == project_id)
    if status:
        q = q.filter(models.Issue.status == status)
    if priority:
        q = q.filter(models.Issue.priority == priority)
    if assignee_id:
        q = q.filter(models.Issue.assignee_id == assignee_id)
    if milestone_id:
        q = q.filter(models.Issue.milestone_id == milestone_id)
    if sprint_id:
        q = q.filter(models.Issue.sprint_id == sprint_id)
    if overdue_only:
        q = q.filter(
            models.Issue.due_date != None,
            models.Issue.due_date < datetime.utcnow(),
            models.Issue.status.notin_([models.Status.resolved, models.Status.closed]),
        )
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Issue.title.ilike(like)) | (models.Issue.description.ilike(like))
        )
    return q.order_by(models.Issue.created_at.desc()).all()


@router.get("/export/csv")
def export_csv(
    project_id: Optional[int] = None,
    status: Optional[models.Status] = None,
    priority: Optional[models.Priority] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    q = db.query(models.Issue)
    if project_id:
        q = q.filter(models.Issue.project_id == project_id)
    if status:
        q = q.filter(models.Issue.status == status)
    if priority:
        q = q.filter(models.Issue.priority == priority)
    issues = q.order_by(models.Issue.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "number", "title", "description", "status", "priority", "type",
        "tags", "assignee", "reporter", "due_date", "created_at", "updated_at",
    ])
    for i in issues:
        writer.writerow([
            i.number,
            i.title,
            i.description,
            i.status.value,
            i.priority.value,
            i.issue_type.value,
            ", ".join(i.tags or []),
            i.assignee.username if i.assignee else "",
            i.reporter.username if i.reporter else "",
            i.due_date.isoformat() if i.due_date else "",
            i.created_at.isoformat() if i.created_at else "",
            i.updated_at.isoformat() if i.updated_at else "",
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=issues_export.csv"},
    )

@router.post("", response_model=schemas.IssueOut)
def create_issue(
    payload: schemas.IssueCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    priority = payload.priority
    issue_type = payload.issue_type
    tags = payload.tags or []
    ai_summary = ""
    ai_confidence = ""

    if payload.use_ai_triage:
        try:
            result = ai_service.triage_issue(payload.title, payload.description)
            priority = priority or models.Priority(result["priority"])
            issue_type = issue_type or models.IssueType(result["issue_type"])
            tags = tags or result.get("tags", [])
            ai_summary = result.get("summary", "")
            ai_confidence = result.get("confidence", "")
        except Exception as e:
            ai_summary = f"(AI triage unavailable: {e})"

    next_number = (
        db.query(func.coalesce(func.max(models.Issue.number), 0))
        .filter(models.Issue.project_id == project.id)
        .scalar()
        + 1
    )

    issue = models.Issue(
        project_id=project.id,
        number=next_number,
        title=payload.title,
        description=payload.description,
        priority=priority or models.Priority.medium,
        issue_type=issue_type or models.IssueType.bug,
        tags=tags,
        ai_summary=ai_summary,
        ai_confidence=ai_confidence,
        reporter_id=current_user.id,
        assignee_id=payload.assignee_id,
        milestone_id=payload.milestone_id,
        sprint_id=payload.sprint_id,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/{issue_id}", response_model=schemas.IssueOut)
def get_issue(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.patch("/{issue_id}", response_model=schemas.IssueOut)
def update_issue(
    issue_id: int,
    payload: schemas.IssueUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    update_data = payload.dict(exclude_unset=True)
    old_assignee_id = issue.assignee_id

    for field, value in update_data.items():
        setattr(issue, field, value)

    db.commit()
    db.refresh(issue)

    if "assignee_id" in update_data and issue.assignee_id and issue.assignee_id != old_assignee_id:
        notif = models.Notification(
            user_id=issue.assignee_id,
            issue_id=issue.id,
            message=f'You were assigned to "{issue.title}"',
        )
        db.add(notif)
        db.commit()

    return issue


@router.delete("/{issue_id}")
def delete_issue(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete(issue)
    db.commit()
    return {"ok": True}


@router.post("/{issue_id}/find-duplicates", response_model=list[schemas.DuplicateCandidate])
def find_duplicates(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    others = (
        db.query(models.Issue)
        .filter(models.Issue.project_id == issue.project_id, models.Issue.id != issue.id)
        .order_by(models.Issue.created_at.desc())
        .limit(30)
        .all()
    )
    existing = [
        {"id": o.id, "number": o.number, "title": o.title, "description": o.description}
        for o in others
    ]
    try:
        candidates = ai_service.find_duplicates(issue.title, issue.description, existing)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI duplicate check failed: {e}")
    return candidates


@router.post("/{issue_id}/comments", response_model=schemas.CommentOut)
def add_comment(
    issue_id: int,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    comment = models.Comment(issue_id=issue_id, user_id=current_user.id, body=payload.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{issue_id}/comments", response_model=list[schemas.CommentOut])
def list_comments(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    return (
        db.query(models.Comment)
        .filter(models.Comment.issue_id == issue_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )


@router.post("/{issue_id}/ai-suggest", response_model=schemas.CommentOut)
def ai_suggest(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    comments = (
        db.query(models.Comment)
        .filter(models.Comment.issue_id == issue_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )
    comment_texts = [c.body for c in comments]

    try:
        suggestion = ai_service.suggest_response(issue.title, issue.description, comment_texts)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI suggestion failed: {e}")

    comment = models.Comment(
        issue_id=issue_id,
        user_id=current_user.id,
        body=suggestion,
        is_ai=1,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{issue_id}/ai-fix-suggestion", response_model=schemas.CommentOut)
def ai_fix_suggestion(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    comments = (
        db.query(models.Comment)
        .filter(models.Comment.issue_id == issue_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )
    comment_texts = [c.body for c in comments]

    try:
        suggestion = ai_service.suggest_code_fix(issue.title, issue.description, comment_texts)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI fix suggestion failed: {e}")

    comment = models.Comment(
        issue_id=issue_id,
        user_id=current_user.id,
        body=suggestion,
        is_ai=1,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{issue_id}/suggest-assignee")
def suggest_assignee(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    users = db.query(models.User).all()
    candidates = []
    for u in users:
        open_count = (
            db.query(models.Issue)
            .filter(
                models.Issue.assignee_id == u.id,
                models.Issue.status.in_([models.Status.open, models.Status.in_progress]),
            )
            .count()
        )
        candidates.append({"id": u.id, "username": u.username, "open_count": open_count})

    try:
        result = ai_service.suggest_assignee(issue.title, issue.description, candidates)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI assignee suggestion failed: {e}")
    return result







@router.post("/{issue_id}/timelogs", response_model=schemas.TimeLogOut)
def add_timelog(
    issue_id: int,
    payload: schemas.TimeLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    log = models.TimeLog(
        issue_id=issue_id,
        user_id=current_user.id,
        hours=payload.hours,
        note=payload.note,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/{issue_id}/timelogs", response_model=list[schemas.TimeLogOut])
def list_timelogs(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    return (
        db.query(models.TimeLog)
        .filter(models.TimeLog.issue_id == issue_id)
        .order_by(models.TimeLog.logged_at.desc())
        .all()
    )


@router.delete("/timelogs/{log_id}")
def delete_timelog(log_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    log = db.query(models.TimeLog).filter(models.TimeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Time log not found")
    if log.user_id != current_user.id and current_user.role != models.Role.admin:
        raise HTTPException(status_code=403, detail="Cannot delete another user's time log")
    db.delete(log)
    db.commit()
    return {"ok": True}


@router.post("/{issue_id}/checklist", response_model=schemas.ChecklistItemOut)
def add_checklist_item(
    issue_id: int,
    payload: schemas.ChecklistItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    item = models.ChecklistItem(issue_id=issue_id, text=payload.text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{issue_id}/checklist", response_model=list[schemas.ChecklistItemOut])
def list_checklist(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    return (
        db.query(models.ChecklistItem)
        .filter(models.ChecklistItem.issue_id == issue_id)
        .order_by(models.ChecklistItem.created_at.asc())
        .all()
    )


@router.patch("/checklist/{item_id}/toggle", response_model=schemas.ChecklistItemOut)
def toggle_checklist_item(item_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    item = db.query(models.ChecklistItem).filter(models.ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    item.is_done = 0 if item.is_done else 1
    db.commit()
    db.refresh(item)
    return item


@router.delete("/checklist/{item_id}")
def delete_checklist_item(item_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    item = db.query(models.ChecklistItem).filter(models.ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}



@router.post("/{issue_id}/analyze-stack-trace")
def analyze_stack_trace_endpoint(
    issue_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    stack_trace = payload.get("stack_trace", "")
    if not stack_trace.strip():
        raise HTTPException(status_code=400, detail="Stack trace is required")

    try:
        result = ai_service.analyze_stack_trace(issue.title, stack_trace)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stack trace analysis failed: {e}")

    return result


import os
import shutil
import uuid

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{issue_id}/attachments", response_model=schemas.AttachmentOut)
async def upload_attachment(
    issue_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(stored_path, "wb") as f:
        content = await file.read()
        f.write(content)

    attachment = models.Attachment(
        issue_id=issue_id,
        uploader_id=current_user.id,
        filename=file.filename,
        stored_path=stored_name,
        content_type=file.content_type or "",
        size_bytes=len(content),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{issue_id}/attachments", response_model=list[schemas.AttachmentOut])
def list_attachments(issue_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    return (
        db.query(models.Attachment)
        .filter(models.Attachment.issue_id == issue_id)
        .order_by(models.Attachment.created_at.desc())
        .all()
    )


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    att = db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path = os.path.join(UPLOAD_DIR, att.stored_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(file_path, filename=att.filename, media_type=att.content_type or "application/octet-stream")


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    att = db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path = os.path.join(UPLOAD_DIR, att.stored_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.delete(att)
    db.commit()
    return {"ok": True}






@router.post("/{issue_id}/compare-assignees")
def compare_assignees(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    users = db.query(models.User).all()
    candidates = []
    for u in users:
        profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == u.id).first()
        active = (
            db.query(models.Issue)
            .filter(
                models.Issue.assignee_id == u.id,
                models.Issue.status.in_([models.Status.open, models.Status.in_progress]),
            )
            .count()
        )
        resolved = (
            db.query(models.Issue)
            .filter(
                models.Issue.assignee_id == u.id,
                models.Issue.status.in_([models.Status.resolved, models.Status.closed]),
            )
            .count()
        )
        candidates.append({
            "id": u.id,
            "username": u.username,
            "skills": profile.skills if profile else [],
            "specialization": profile.specialization if profile else "",
            "experience_years": profile.experience_years if profile else 0,
            "active_issue_count": active,
            "resolved_issue_count": resolved,
        })

    try:
        results = ai_service.compare_assignee_candidates(issue.title, issue.description, candidates)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Comparison failed: {e}")

    return results


@router.post("/{issue_id}/estimate-metrics")
def estimate_metrics(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    comments = (
        db.query(models.Comment)
        .filter(models.Comment.issue_id == issue_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )
    comment_texts = [c.body for c in comments]

    try:
        result = ai_service.estimate_issue_metrics(
            issue.title, issue.description, issue.priority.value, comment_texts
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Metric estimation failed: {e}")

    return result
