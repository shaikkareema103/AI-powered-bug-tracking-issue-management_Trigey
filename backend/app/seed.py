"""
Seeds demo data on startup so the live deployment always has realistic
data to explore, even after Render wipes the ephemeral SQLite file on
restart. Safe to call every startup: skips anything that already exists,
and never touches accounts people register themselves.
"""
from datetime import datetime, timedelta

from .database import SessionLocal
from . import models, auth


def seed_demo_data():
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        def get_or_create_user(username, email, password, role, skills, specialization, years, bio):
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                return user
            user = models.User(
                username=username, email=email,
                password_hash=auth.hash_password(password), role=role,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            db.add(models.UserProfile(
                user_id=user.id, skills=skills, specialization=specialization,
                experience_years=years, bio=bio,
            ))
            db.commit()
            return user

        def get_or_create_project(key, name, description, created_by):
            project = db.query(models.Project).filter(models.Project.key == key).first()
            if project:
                return project, False
            project = models.Project(key=key, name=name, description=description, created_by=created_by)
            db.add(project)
            db.commit()
            db.refresh(project)
            return project, True

        def add_issue(project, number, title, description, status, priority, issue_type,
                      reporter, assignee=None, tags=None, milestone=None, sprint=None,
                      due_offset_days=None, ai_summary="", ai_confidence="", pr_link="",
                      duplicate_of=None):
            due_date = now + timedelta(days=due_offset_days) if due_offset_days is not None else None
            issue = models.Issue(
                project_id=project.id, number=number, title=title, description=description,
                status=status, priority=priority, issue_type=issue_type, tags=tags or [],
                reporter_id=reporter.id, assignee_id=assignee.id if assignee else None,
                milestone_id=milestone.id if milestone else None,
                sprint_id=sprint.id if sprint else None, due_date=due_date,
                ai_summary=ai_summary, ai_confidence=ai_confidence, pr_link=pr_link,
                duplicate_of=duplicate_of,
                created_at=now - timedelta(days=14) + timedelta(hours=number),
            )
            db.add(issue)
            db.commit()
            db.refresh(issue)
            return issue

        def add_comment(issue, user, body, is_ai=0, days_ago=1):
            db.add(models.Comment(
                issue_id=issue.id, user_id=user.id, body=body, is_ai=is_ai,
                created_at=now - timedelta(days=days_ago),
            ))
            db.commit()

        def add_checklist(issue, items):
            for text, done in items:
                db.add(models.ChecklistItem(issue_id=issue.id, text=text, is_done=1 if done else 0))
            db.commit()

        def add_sla(project, name, priority, hours):
            db.add(models.SLAPolicy(project_id=project.id, name=name, priority=priority, resolution_hours=hours))
            db.commit()

        admin = db.query(models.User).filter(models.User.role == models.Role.admin).first()
        if not admin:
            admin = get_or_create_user(
                "admin", "admin@triagey.dev", "admin123", models.Role.admin,
                ["management", "architecture"], "Engineering Lead", 8,
                "Oversees delivery across all active projects.",
            )

        priya = get_or_create_user("priya_dev", "priya@triagey.dev", "password123", models.Role.member,
            ["python", "fastapi", "postgresql"], "Backend Engineer", 4, "Owns the API and data layer.")
        marco = get_or_create_user("marco_fe", "marco@triagey.dev", "password123", models.Role.member,
            ["react", "typescript", "css"], "Frontend Engineer", 3, "Builds and maintains the customer-facing UI.")
        lena = get_or_create_user("lena_qa", "lena@triagey.dev", "password123", models.Role.member,
            ["testing", "automation", "ci/cd"], "QA Engineer", 5, "Runs regression and owns the release checklist.")
        raj = get_or_create_user("raj_mobile", "raj@triagey.dev", "password123", models.Role.member,
            ["kotlin", "swift", "mobile"], "Mobile Engineer", 6, "Ships the iOS and Android apps.")

        shop, created = get_or_create_project("SHOP", "Storefront", "Customer-facing e-commerce site and checkout flow.", admin.id)
        if created:
            m1 = models.Milestone(project_id=shop.id, title="Checkout redesign", description="Ship the new one-page checkout.", due_date=now + timedelta(days=10), status=models.MilestoneStatus.open)
            m2 = models.Milestone(project_id=shop.id, title="Q3 launch", description="General availability for Q3 features.", due_date=now - timedelta(days=3), status=models.MilestoneStatus.open)
            db.add_all([m1, m2]); db.commit(); db.refresh(m1); db.refresh(m2)

            sp1 = models.Sprint(project_id=shop.id, name="Sprint 12", goal="Finish checkout redesign", start_date=now - timedelta(days=14), end_date=now, status=models.SprintStatus.completed)
            sp2 = models.Sprint(project_id=shop.id, name="Sprint 13", goal="Payment provider migration", start_date=now, end_date=now + timedelta(days=14), status=models.SprintStatus.active)
            db.add_all([sp1, sp2]); db.commit(); db.refresh(sp1); db.refresh(sp2)

            i1 = add_issue(shop, 1, "Checkout fails when applying two discount codes",
                "Stacking a percentage code with a free-shipping code throws a 500 on /api/cart/apply-discount.",
                models.Status.open, models.Priority.critical, models.IssueType.bug,
                reporter=lena, assignee=priya, tags=["checkout", "payments"], milestone=m1, sprint=sp2,
                due_offset_days=-1, ai_summary="Likely an unhandled case where two discount rows conflict in the totals calculation.", ai_confidence="high")
            add_comment(i1, lena, "Repro: add a %-off code, then a free-shipping code, then click Apply again.", days_ago=2)
            add_comment(i1, priya, "Confirmed - the discount stacking check assumes only one active code.", days_ago=1)
            add_checklist(i1, [("Reproduce locally", True), ("Patch discount stacking logic", False), ("Add regression test", False)])

            add_issue(shop, 2, "Product images lazy-load flickers on Safari", "Images pop in at the wrong size before settling, causing layout shift.",
                models.Status.in_progress, models.Priority.medium, models.IssueType.bug, reporter=marco, assignee=marco, tags=["frontend", "safari"], sprint=sp2, due_offset_days=5)

            add_issue(shop, 3, "Add saved payment methods to account page", "Let returning customers store a card for faster checkout.",
                models.Status.open, models.Priority.high, models.IssueType.feature, reporter=admin, assignee=priya, tags=["checkout", "account"], milestone=m1, sprint=sp2, due_offset_days=8)

            i4 = add_issue(shop, 4, "Cart total rounds incorrectly with 3-decimal currencies", "JOD and other 3-decimal currencies round to 2dp, undercharging by a fraction.",
                models.Status.resolved, models.Priority.high, models.IssueType.bug, reporter=priya, assignee=priya, tags=["payments", "i18n"], milestone=m2)
            add_comment(i4, priya, "Fixed by switching to the currency's minor-unit precision from Intl.NumberFormat.", days_ago=4)

            add_issue(shop, 5, "Wishlist button unresponsive on mobile Chrome", "Tap target for the heart icon is too small and sometimes double-fires.",
                models.Status.closed, models.Priority.low, models.IssueType.bug, reporter=marco, assignee=marco, tags=["frontend", "mobile"])

            add_issue(shop, 6, "Evaluate Stripe vs Adyen for EU expansion", "Compare fees, payout speed, and 3DS2 support for our new EU storefronts.",
                models.Status.open, models.Priority.medium, models.IssueType.question, reporter=admin, tags=["payments", "research"], sprint=sp2, due_offset_days=12)

            add_issue(shop, 7, "Checkout button briefly unclickable after error toast", "A leftover overlay from the error toast blocks the button for ~1s.",
                models.Status.open, models.Priority.medium, models.IssueType.bug, reporter=lena, tags=["checkout"], duplicate_of=i1.id)

            add_issue(shop, 8, "Add order history export to CSV", "Customers want to download their order history for expense reports.",
                models.Status.open, models.Priority.low, models.IssueType.feature, reporter=admin, milestone=m2, due_offset_days=20)

            add_sla(shop, "Critical response", models.Priority.critical, 4)
            add_sla(shop, "High response", models.Priority.high, 24)
            add_sla(shop, "Medium response", models.Priority.medium, 72)
            add_sla(shop, "Low response", models.Priority.low, 168)

        mobl, created = get_or_create_project("MOBL", "Mobile Banking", "iOS and Android app for account management and transfers.", admin.id)
        if created:
            m1 = models.Milestone(project_id=mobl.id, title="Biometric login", description="Face ID / fingerprint sign-in.", due_date=now + timedelta(days=15), status=models.MilestoneStatus.open)
            m2 = models.Milestone(project_id=mobl.id, title="v2.4 release", description="App store submission for v2.4.", due_date=now - timedelta(days=1), status=models.MilestoneStatus.open)
            db.add_all([m1, m2]); db.commit(); db.refresh(m1); db.refresh(m2)

            sp1 = models.Sprint(project_id=mobl.id, name="Sprint 7", goal="Biometric login groundwork", start_date=now - timedelta(days=7), end_date=now + timedelta(days=7), status=models.SprintStatus.active)
            db.add(sp1); db.commit(); db.refresh(sp1)

            j1 = add_issue(mobl, 1, "App crashes on transfer confirmation screen (Android 14)", "Crash log points to a null balance object when the transfer amount equals the full balance.",
                models.Status.open, models.Priority.critical, models.IssueType.bug, reporter=lena, assignee=raj, tags=["crash", "android"], sprint=sp1, due_offset_days=-2,
                ai_summary="Null pointer when remaining balance hits exactly zero after a full-balance transfer.", ai_confidence="high")
            add_comment(j1, raj, "Can confirm - balance object isn't re-fetched before the confirmation render.", days_ago=1)

            add_issue(mobl, 2, "Face ID prompt doesn't reappear after backgrounding app", "If the user backgrounds the app during Face ID and returns, login hangs.",
                models.Status.in_progress, models.Priority.high, models.IssueType.bug, reporter=raj, assignee=raj, tags=["ios", "auth"], milestone=m1, sprint=sp1, due_offset_days=6)

            add_issue(mobl, 3, "Add spending insights chart to home screen", "Monthly category breakdown, similar to the web dashboard.",
                models.Status.open, models.Priority.medium, models.IssueType.feature, reporter=admin, tags=["android", "ios"], due_offset_days=25)

            add_issue(mobl, 4, "Push notification for large transactions delayed 10+ minutes", "Notifications should fire within seconds for fraud-prevention purposes.",
                models.Status.open, models.Priority.critical, models.IssueType.bug, reporter=admin, assignee=priya, tags=["backend", "notifications"], sprint=sp1, due_offset_days=-1)

            j5 = add_issue(mobl, 5, "Dark mode: transfer amount text unreadable", "Low contrast gray-on-black in the amount input field.",
                models.Status.resolved, models.Priority.low, models.IssueType.bug, reporter=marco, assignee=raj, tags=["ios", "android", "accessibility"])
            add_comment(j5, raj, "Bumped text color to the high-contrast token used elsewhere in dark mode.", days_ago=3)

            add_issue(mobl, 6, "Support recurring transfers", "Let users schedule weekly/monthly transfers between their own accounts.",
                models.Status.open, models.Priority.medium, models.IssueType.feature, reporter=admin, milestone=m2, due_offset_days=30)

            add_sla(mobl, "Critical response", models.Priority.critical, 2)
            add_sla(mobl, "High response", models.Priority.high, 12)
            add_sla(mobl, "Medium response", models.Priority.medium, 48)

        print("[seed] demo data check complete")
    finally:
        db.close()
