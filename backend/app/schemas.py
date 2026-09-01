from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from .models import Role, Status, Priority, IssueType, MilestoneStatus, SprintStatus


# ---------- Auth ----------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Role

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


class RoleUpdate(BaseModel):
    role: Role


# ---------- Projects ----------
class ProjectCreate(BaseModel):
    key: str
    name: str
    description: str = ""


class ProjectOut(BaseModel):
    id: int
    key: str
    name: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Milestones ----------
class MilestoneMini(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class MilestoneCreate(BaseModel):
    project_id: int
    title: str
    description: str = ""
    due_date: Optional[datetime] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[MilestoneStatus] = None


class MilestoneOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    due_date: Optional[datetime] = None
    status: MilestoneStatus
    created_at: datetime
    issue_count: int = 0
    done_count: int = 0

    class Config:
        from_attributes = True


# ---------- Sprints ----------
class SprintMini(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class SprintCreate(BaseModel):
    project_id: int
    name: str
    goal: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[SprintStatus] = None


class SprintOut(BaseModel):
    id: int
    project_id: int
    name: str
    goal: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: SprintStatus
    created_at: datetime
    issue_count: int = 0
    done_count: int = 0

    class Config:
        from_attributes = True


# ---------- Issues ----------
class IssueCreate(BaseModel):
    project_id: int
    title: str
    description: str = ""
    priority: Optional[Priority] = None
    issue_type: Optional[IssueType] = None
    tags: Optional[List[str]] = None
    assignee_id: Optional[int] = None
    milestone_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[datetime] = None
    pr_link: str = ""
    use_ai_triage: bool = True


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    issue_type: Optional[IssueType] = None
    tags: Optional[List[str]] = None
    assignee_id: Optional[int] = None
    milestone_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[datetime] = None
    pr_link: Optional[str] = None


class UserMini(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class IssueOut(BaseModel):
    id: int
    project_id: int
    number: int
    title: str
    description: str
    status: Status
    priority: Priority
    issue_type: IssueType
    tags: List[str] = []
    ai_summary: str = ""
    ai_confidence: str = ""
    duplicate_of: Optional[int] = None
    milestone_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[datetime] = None
    pr_link: str = ""
    milestone: Optional[MilestoneMini] = None
    sprint: Optional[SprintMini] = None
    reporter: Optional[UserMini]
    assignee: Optional[UserMini]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Comments ----------
class CommentCreate(BaseModel):
    body: str


class CommentOut(BaseModel):
    id: int
    issue_id: int
    body: str
    is_ai: int
    user: Optional[UserMini]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- AI ----------
class TriageResult(BaseModel):
    priority: Priority
    severity: str
    issue_type: IssueType
    tags: List[str]
    summary: str
    confidence: str


class DuplicateCandidate(BaseModel):
    issue_id: int
    number: int
    title: str
    confidence: str
    reason: str


class LiveDuplicateCheck(BaseModel):
    project_id: int
    title: str
    description: str = ""



class TimeLogCreate(BaseModel):
    hours: float
    note: str = ""


class TimeLogOut(BaseModel):
    id: int
    issue_id: int
    hours: float
    note: str
    user: Optional[UserMini]
    logged_at: datetime

    class Config:
        from_attributes = True





class ChecklistItemCreate(BaseModel):
    text: str


class ChecklistItemOut(BaseModel):
    id: int
    issue_id: int
    text: str
    is_done: int
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    issue_id: Optional[int] = None
    message: str
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentOut(BaseModel):
    id: int
    issue_id: int
    filename: str
    content_type: str
    size_bytes: int
    uploader: Optional[UserMini]
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    skills: Optional[List[str]] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None


class UserProfileOut(BaseModel):
    user_id: int
    username: str
    skills: List[str] = []
    specialization: str = ""
    experience_years: int = 0
    bio: str = ""
    active_issue_count: int = 0
    resolved_issue_count: int = 0

    class Config:
        from_attributes = True


class SLAPolicyCreate(BaseModel):
    project_id: int
    name: str
    priority: Priority
    resolution_hours: int
    escalate_to_role: str = "admin"


class SLAPolicyOut(BaseModel):
    id: int
    project_id: int
    name: str
    priority: Priority
    resolution_hours: int
    escalate_to_role: str
    created_at: datetime

    class Config:
        from_attributes = True
