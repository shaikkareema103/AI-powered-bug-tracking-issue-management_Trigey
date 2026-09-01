import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, Float
)
from sqlalchemy.orm import relationship
from .database import Base


class Role(str, enum.Enum):
    admin = "admin"
    member = "member"


class Status(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IssueType(str, enum.Enum):
    bug = "bug"
    feature = "feature"
    task = "task"
    question = "question"


class MilestoneStatus(str, enum.Enum):
    open = "open"
    completed = "completed"


class SprintStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    completed = "completed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(Role), default=Role.member, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    reported_issues = relationship(
        "Issue", back_populates="reporter", foreign_keys="Issue.reporter_id"
    )
    assigned_issues = relationship(
        "Issue", back_populates="assignee", foreign_keys="Issue.assignee_id"
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(10), unique=True, index=True, nullable=False)  # e.g. "ENG"
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    due_date = Column(DateTime, nullable=True)
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.open, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")
    issues = relationship("Issue", back_populates="milestone")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    goal = Column(Text, default="")
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(Enum(SprintStatus), default=SprintStatus.planned, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="sprints")
    issues = relationship("Issue", back_populates="sprint")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    number = Column(Integer, nullable=False)  # per-project sequential number

    title = Column(String(255), nullable=False)
    description = Column(Text, default="")

    status = Column(Enum(Status), default=Status.open, nullable=False)
    priority = Column(Enum(Priority), default=Priority.medium, nullable=False)
    issue_type = Column(Enum(IssueType), default=IssueType.bug, nullable=False)

    tags = Column(JSON, default=list)  # list[str]

    ai_summary = Column(Text, default="")
    ai_confidence = Column(String(16), default="")  # low/medium/high, set by AI triage
    duplicate_of = Column(Integer, ForeignKey("issues.id"), nullable=True)

    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    pr_link = Column(String(500), default="")

    reporter_id = Column(Integer, ForeignKey("users.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="issues")
    reporter = relationship("User", back_populates="reported_issues", foreign_keys=[reporter_id])
    assignee = relationship("User", back_populates="assigned_issues", foreign_keys=[assignee_id])
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
    milestone = relationship("Milestone", back_populates="issues")
    sprint = relationship("Sprint", back_populates="issues")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    is_ai = Column(Integer, default=0)  # 1 if generated by the AI assistant
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="comments")
    user = relationship("User")




class TimeLog(Base):
    __tablename__ = "time_logs"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hours = Column(Float, nullable=False)
    note = Column(Text, default="")
    logged_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue")
    user = relationship("User")





class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    text = Column(String(255), nullable=False)
    is_done = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=True)
    message = Column(String(500), nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    issue = relationship("Issue")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    content_type = Column(String(100), default="")
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue")
    uploader = relationship("User")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    skills = Column(JSON, default=list)
    specialization = Column(String(128), default="")
    experience_years = Column(Integer, default=0)
    bio = Column(Text, default="")

    user = relationship("User")


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(128), nullable=False)
    priority = Column(Enum(Priority), nullable=False)
    resolution_hours = Column(Integer, nullable=False)
    escalate_to_role = Column(String(32), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
