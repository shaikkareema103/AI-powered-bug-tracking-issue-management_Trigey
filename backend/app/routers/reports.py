from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, auth, ai_service
from ..database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/weekly")
def weekly_report(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    since = datetime.utcnow() - timedelta(days=7)

    issues_q = db.query(models.Issue)
    if project_id:
        issues_q = issues_q.filter(models.Issue.project_id == project_id)

    created = issues_q.filter(models.Issue.created_at >= since).all()
    resolved = issues_q.filter(
        models.Issue.status.in_([models.Status.resolved, models.Status.closed]),
        models.Issue.updated_at >= since,
    ).all()

    comments_q = db.query(models.Comment).filter(models.Comment.created_at >= since)
    if project_id:
        comments_q = comments_q.join(models.Issue).filter(models.Issue.project_id == project_id)
    comments_count = comments_q.count()

    tag_counts = {}
    for i in created:
        for t in (i.tags or []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:5]

    project = db.query(models.Project).filter(models.Project.id == project_id).first() if project_id else None
    project_name = project.name if project else "all projects"

    try:
        report_text = ai_service.generate_weekly_report(
            project_name,
            [{"title": i.title, "priority": i.priority.value} for i in created],
            [{"title": i.title} for i in resolved],
            comments_count,
            [t for t, _ in top_tags],
        )
    except Exception as e:
        report_text = f"(AI report unavailable: {e})"

    return {
        "report": report_text,
        "created_count": len(created),
        "resolved_count": len(resolved),
        "comments_count": comments_count,
        "top_tags": [t for t, _ in top_tags],
    }


@router.post("/activity")
def activity_summary(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    since = datetime.utcnow() - timedelta(days=14)

    issues_q = db.query(models.Issue)
    if project_id:
        issues_q = issues_q.filter(models.Issue.project_id == project_id)
    recent_issues = issues_q.filter(models.Issue.created_at >= since).order_by(models.Issue.created_at.desc()).limit(15).all()

    comments_q = db.query(models.Comment).filter(models.Comment.created_at >= since, models.Comment.is_ai == 0)
    if project_id:
        comments_q = comments_q.join(models.Issue).filter(models.Issue.project_id == project_id)
    recent_comments = comments_q.order_by(models.Comment.created_at.desc()).limit(15).all()

    project = db.query(models.Project).filter(models.Project.id == project_id).first() if project_id else None
    project_name = project.name if project else "all projects"

    items = []
    for i in recent_issues:
        items.append({"type": "issue created", "text": f'"{i.title}" ({i.priority.value} priority)', "when": i.created_at.strftime("%b %d")})
    for c in recent_comments:
        items.append({"type": "comment", "text": c.body[:100], "when": c.created_at.strftime("%b %d")})
    items.sort(key=lambda x: x["when"], reverse=True)

    if not items:
        return {"summary": "No recent activity to summarize.", "item_count": 0}

    try:
        summary_text = ai_service.summarize_activity(project_name, items)
    except Exception as e:
        summary_text = f"(AI summary unavailable: {e})"

    return {"summary": summary_text, "item_count": len(items)}
