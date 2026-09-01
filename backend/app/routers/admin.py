from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), current_user=Depends(auth.require_admin)):
    total_users = db.query(models.User).count()
    total_projects = db.query(models.Project).count()
    total_issues = db.query(models.Issue).count()
    ai_triaged = db.query(models.Issue).filter(models.Issue.ai_summary != "").count()
    ai_comments = db.query(models.Comment).filter(models.Comment.is_ai == 1).count()
    admin_count = db.query(models.User).filter(models.User.role == models.Role.admin).count()
    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_issues": total_issues,
        "ai_triaged_issues": ai_triaged,
        "ai_comments": ai_comments,
        "admin_count": admin_count,
    }


@router.get("/users", response_model=list[schemas.UserOut])
def list_all_users(db: Session = Depends(get_db), current_user=Depends(auth.require_admin)):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.patch("/users/{user_id}/role", response_model=schemas.UserOut)
def change_user_role(
    user_id: int,
    payload: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.get("/projects", response_model=list[schemas.ProjectOut])
def list_all_projects(db: Session = Depends(get_db), current_user=Depends(auth.require_admin)):
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_admin),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.get("/issues", response_model=list[schemas.IssueOut])
def list_all_issues(db: Session = Depends(get_db), current_user=Depends(auth.require_admin)):
    return db.query(models.Issue).order_by(models.Issue.created_at.desc()).all()


@router.delete("/issues/{issue_id}")
def delete_any_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_admin),
):
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete(issue)
    db.commit()
    return {"ok": True}
