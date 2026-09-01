import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import auth as auth_router
from .routers import projects as projects_router
from .routers import issues as issues_router
from .routers import dashboard as dashboard_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Bug Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(projects_router.router)
app.include_router(issues_router.router)
app.include_router(dashboard_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the frontend (static files) from the same server
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
from .routers import admin as admin_router
app.include_router(admin_router.router)

from .routers import milestones as milestones_router
from .routers import sprints as sprints_router
app.include_router(milestones_router.router)
app.include_router(sprints_router.router)

from .routers import reports as reports_router
app.include_router(reports_router.router)

from .routers import notifications as notifications_router
app.include_router(notifications_router.router)

from .routers import profiles as profiles_router
app.include_router(profiles_router.router)

from .routers import sla as sla_router
app.include_router(sla_router.router)

from .routers import chat as chat_router
app.include_router(chat_router.router)

