"""
Seed script for Triagey — creates realistic multi-project test data
covering every feature: issues across all statuses/priorities/types,
milestones, sprints, comments, checklists, SLA policies, user profiles.

Run from backend/ with:  python seed_data.py
Safe to re-run: skips anything that already exists.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

now = datetime.utcnow()


def get_or_create_user(username, email, password, role, skills, specialization, years, bio):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        return user
    user = models.User(
        username=username,
        email=email,
        password_hash=auth.hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    profile = models.UserProfile(
        user_id=user.id,
        skills=skills,
        specialization=specialization,
        experience_years=years,
        bio=bio,
    )
    db.add(profile)
    db.commit()
    return user


def get_or_create_project(key, name, description, created_by):
    project = db.query(models.Project).filter(models.Project.key == key).first()
    if project:
        print(f"  project {key} already exists, skipping")
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
        project_id=project.id,
        number=number,
        title=title,
        description=description,
        status=status,
        priority=priority,
        issue_type=issue_type,
        tags=tags or [],
        reporter_id=reporter.id,
        assignee_id=assignee.id if assignee else None,
        milestone_id=milestone.id if milestone else None,
        sprint_id=sprint.id if sprint else None,
        due_date=due_date,
        ai_summary=ai_summary,
        ai_confidence=ai_confidence,
        pr_link=pr_link,
        duplicate_of=duplicate_of,
        created_at=now - timedelta(days=14) + timedelta(hours=number),
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def add_comment(issue, user, body, is_ai=0, days_ago=1):
    c = models.Comment(
        issue_id=issue.id,
        user_id=user.id,
        body=body,
        is_ai=is_ai,
        created_at=now - timedelta(days=days_ago),
    )
    db.add(c)
    db.commit()


def add_checklist(issue, items):
    for text, done in items:
        db.add(models.ChecklistItem(issue_id=issue.id, text=text, is_done=1 if done else 0))
    db.commit()


def add_sla(project, name, priority, hours):
    db.add(models.SLAPolicy(project_id=project.id, name=name, priority=priority, resolution_hours=hours))
    db.commit()


def get_or_create_sprint(project, name, goal, start_date, end_date, status):
    sp = db.query(models.Sprint).filter(models.Sprint.project_id == project.id, models.Sprint.name == name).first()
    if sp:
        return sp
    sp = models.Sprint(project_id=project.id, name=name, goal=goal, start_date=start_date, end_date=end_date, status=status)
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return sp


print("Creating users...")
admin = db.query(models.User).filter(models.User.role == models.Role.admin).first()
if not admin:
    admin = get_or_create_user(
        "admin", "admin@triagey.dev", "admin123", models.Role.admin,
        ["management", "architecture"], "Engineering Lead", 8,
        "Oversees delivery across all active projects.",
    )

priya = get_or_create_user(
    "priya_dev", "priya@triagey.dev", "password123", models.Role.member,
    ["python", "fastapi", "postgresql"], "Backend Engineer", 4,
    "Owns the API and data layer.",
)
marco = get_or_create_user(
    "marco_fe", "marco@triagey.dev", "password123", models.Role.member,
    ["react", "typescript", "css"], "Frontend Engineer", 3,
    "Builds and maintains the customer-facing UI.",
)
lena = get_or_create_user(
    "lena_qa", "lena@triagey.dev", "password123", models.Role.member,
    ["testing", "automation", "ci/cd"], "QA Engineer", 5,
    "Runs regression and owns the release checklist.",
)
raj = get_or_create_user(
    "raj_mobile", "raj@triagey.dev", "password123", models.Role.member,
    ["kotlin", "swift", "mobile"], "Mobile Engineer", 6,
    "Ships the iOS and Android apps.",
)
devon = get_or_create_user(
    "devon_devops", "devon@triagey.dev", "password123", models.Role.member,
    ["docker", "kubernetes", "ci/cd"], "DevOps Engineer", 5,
    "Owns deploys, infra, and monitoring.",
)
sara = get_or_create_user(
    "sara_design", "sara@triagey.dev", "password123", models.Role.member,
    ["figma", "ux research", "design systems"], "Product Designer", 4,
    "Designs flows and maintains the component library.",
)
tom = get_or_create_user(
    "tom_backend", "tom@triagey.dev", "password123", models.Role.member,
    ["node", "graphql", "redis"], "Backend Engineer", 3,
    "Works on APIs and background jobs.",
)
nina = get_or_create_user(
    "nina_pm", "nina@triagey.dev", "password123", models.Role.member,
    ["roadmapping", "stakeholder management"], "Product Manager", 7,
    "Prioritizes the backlog and writes specs.",
)
alex_fe = get_or_create_user(
    "alex_fe2", "alex@triagey.dev", "password123", models.Role.member,
    ["vue", "accessibility", "css"], "Frontend Engineer", 2,
    "Focuses on accessibility and polish.",
)

print("Seeding SHOP project...")
shop, created = get_or_create_project(
    "SHOP", "Storefront", "Customer-facing e-commerce site and checkout flow.", admin.id
)
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
        due_offset_days=-1,
        ai_summary="Likely an unhandled case where two discount rows conflict in the totals calculation.",
        ai_confidence="high")
    add_comment(i1, lena, "Repro: add a %-off code, then a free-shipping code, then click Apply again.", days_ago=2)
    add_comment(i1, priya, "Confirmed - the discount stacking check assumes only one active code.", days_ago=1)
    add_checklist(i1, [("Reproduce locally", True), ("Patch discount stacking logic", False), ("Add regression test", False)])

    i2 = add_issue(shop, 2, "Product images lazy-load flickers on Safari",
        "Images pop in at the wrong size before settling, causing layout shift.",
        models.Status.in_progress, models.Priority.medium, models.IssueType.bug,
        reporter=marco, assignee=marco, tags=["frontend", "safari"], sprint=sp2, due_offset_days=5)

    i3 = add_issue(shop, 3, "Add saved payment methods to account page",
        "Let returning customers store a card for faster checkout.",
        models.Status.open, models.Priority.high, models.IssueType.feature,
        reporter=admin, assignee=priya, tags=["checkout", "account"], milestone=m1, sprint=sp2, due_offset_days=8)

    i4 = add_issue(shop, 4, "Cart total rounds incorrectly with 3-decimal currencies",
        "JOD and other 3-decimal currencies round to 2dp, undercharging by a fraction.",
        models.Status.resolved, models.Priority.high, models.IssueType.bug,
        reporter=priya, assignee=priya, tags=["payments", "i18n"], milestone=m2)
    add_comment(i4, priya, "Fixed by switching to the currency's minor-unit precision from Intl.NumberFormat.", days_ago=4)

    i5 = add_issue(shop, 5, "Wishlist button unresponsive on mobile Chrome",
        "Tap target for the heart icon is too small and sometimes double-fires.",
        models.Status.closed, models.Priority.low, models.IssueType.bug,
        reporter=marco, assignee=marco, tags=["frontend", "mobile"])

    i6 = add_issue(shop, 6, "Evaluate Stripe vs Adyen for EU expansion",
        "Compare fees, payout speed, and 3DS2 support for our new EU storefronts.",
        models.Status.open, models.Priority.medium, models.IssueType.question,
        reporter=admin, tags=["payments", "research"], sprint=sp2, due_offset_days=12)

    i7 = add_issue(shop, 7, "Checkout button briefly unclickable after error toast",
        "A leftover overlay from the error toast blocks the button for ~1s.",
        models.Status.open, models.Priority.medium, models.IssueType.bug,
        reporter=lena, tags=["checkout"], duplicate_of=i1.id)

    i8 = add_issue(shop, 8, "Add order history export to CSV",
        "Customers want to download their order history for expense reports.",
        models.Status.open, models.Priority.low, models.IssueType.feature,
        reporter=admin, milestone=m2, due_offset_days=20)

    add_sla(shop, "Critical response", models.Priority.critical, 4)
    add_sla(shop, "High response", models.Priority.high, 24)
    add_sla(shop, "Medium response", models.Priority.medium, 72)
    add_sla(shop, "Low response", models.Priority.low, 168)
    print("  SHOP: 8 issues, 2 milestones, 2 sprints, SLA policies")
else:
    shop = db.query(models.Project).filter(models.Project.key == "SHOP").first()

print("Seeding MOBL project...")
mobl, created = get_or_create_project(
    "MOBL", "Mobile Banking", "iOS and Android app for account management and transfers.", admin.id
)
if created:
    m1 = models.Milestone(project_id=mobl.id, title="Biometric login", description="Face ID / fingerprint sign-in.", due_date=now + timedelta(days=15), status=models.MilestoneStatus.open)
    m2 = models.Milestone(project_id=mobl.id, title="v2.4 release", description="App store submission for v2.4.", due_date=now - timedelta(days=1), status=models.MilestoneStatus.open)
    db.add_all([m1, m2]); db.commit(); db.refresh(m1); db.refresh(m2)

    sp1 = models.Sprint(project_id=mobl.id, name="Sprint 7", goal="Biometric login groundwork", start_date=now - timedelta(days=7), end_date=now + timedelta(days=7), status=models.SprintStatus.active)
    db.add(sp1); db.commit(); db.refresh(sp1)

    j1 = add_issue(mobl, 1, "App crashes on transfer confirmation screen (Android 14)",
        "Crash log points to a null balance object when the transfer amount equals the full balance.",
        models.Status.open, models.Priority.critical, models.IssueType.bug,
        reporter=lena, assignee=raj, tags=["crash", "android"], sprint=sp1, due_offset_days=-2,
        ai_summary="Null pointer when remaining balance hits exactly zero after a full-balance transfer.",
        ai_confidence="high")
    add_comment(j1, raj, "Can confirm - balance object isn't re-fetched before the confirmation render.", days_ago=1)

    j2 = add_issue(mobl, 2, "Face ID prompt doesn't reappear after backgrounding app",
        "If the user backgrounds the app during Face ID and returns, login hangs.",
        models.Status.in_progress, models.Priority.high, models.IssueType.bug,
        reporter=raj, assignee=raj, tags=["ios", "auth"], milestone=m1, sprint=sp1, due_offset_days=6)

    j3 = add_issue(mobl, 3, "Add spending insights chart to home screen",
        "Monthly category breakdown, similar to the web dashboard.",
        models.Status.open, models.Priority.medium, models.IssueType.feature,
        reporter=admin, tags=["android", "ios"], due_offset_days=25)

    j4 = add_issue(mobl, 4, "Push notification for large transactions delayed 10+ minutes",
        "Notifications should fire within seconds for fraud-prevention purposes.",
        models.Status.open, models.Priority.critical, models.IssueType.bug,
        reporter=admin, assignee=priya, tags=["backend", "notifications"], sprint=sp1, due_offset_days=-1)

    j5 = add_issue(mobl, 5, "Dark mode: transfer amount text unreadable",
        "Low contrast gray-on-black in the amount input field.",
        models.Status.resolved, models.Priority.low, models.IssueType.bug,
        reporter=marco, assignee=raj, tags=["ios", "android", "accessibility"])
    add_comment(j5, raj, "Bumped text color to the high-contrast token used elsewhere in dark mode.", days_ago=3)

    j6 = add_issue(mobl, 6, "Support recurring transfers",
        "Let users schedule weekly/monthly transfers between their own accounts.",
        models.Status.open, models.Priority.medium, models.IssueType.feature,
        reporter=admin, milestone=m2, due_offset_days=30)

    add_sla(mobl, "Critical response", models.Priority.critical, 2)
    add_sla(mobl, "High response", models.Priority.high, 12)
    add_sla(mobl, "Medium response", models.Priority.medium, 48)
    print("  MOBL: 6 issues, 2 milestones, 1 sprint, SLA policies")
else:
    mobl = db.query(models.Project).filter(models.Project.key == "MOBL").first()

def seed_project(key, name, description, milestone_defs, sprint_defs, issue_defs, sla_defs):
    """Generic full-detail project seeder. Returns (project, created)."""
    project, created = get_or_create_project(key, name, description, admin.id)
    if not created:
        return project, False

    milestones = {}
    for mkey, title, desc, due_offset in milestone_defs:
        m = models.Milestone(
            project_id=project.id, title=title, description=desc,
            due_date=now + timedelta(days=due_offset), status=models.MilestoneStatus.open,
        )
        db.add(m); db.commit(); db.refresh(m)
        milestones[mkey] = m

    sprints = {}
    for skey, sname, goal, start_offset, end_offset, status in sprint_defs:
        sp = models.Sprint(
            project_id=project.id, name=sname, goal=goal,
            start_date=now + timedelta(days=start_offset), end_date=now + timedelta(days=end_offset),
            status=status,
        )
        db.add(sp); db.commit(); db.refresh(sp)
        sprints[skey] = sp

    issues = {}
    for idef in issue_defs:
        num, title, desc, status, priority, itype, reporter, assignee, tags, mkey, skey, due_offset, ai_summary, ai_conf, dup_of_key, comments, checklist = idef
        issue = add_issue(
            project, num, title, desc, status, priority, itype,
            reporter=reporter, assignee=assignee, tags=tags,
            milestone=milestones.get(mkey) if mkey else None,
            sprint=sprints.get(skey) if skey else None,
            due_offset_days=due_offset, ai_summary=ai_summary, ai_confidence=ai_conf,
            duplicate_of=issues[dup_of_key].id if dup_of_key else None,
        )
        issues[num] = issue
        for c_user, c_body, c_days_ago in comments:
            add_comment(issue, c_user, c_body, days_ago=c_days_ago)
        if checklist:
            add_checklist(issue, checklist)

    for sname, spriority, shours in sla_defs:
        add_sla(project, sname, spriority, shours)

    print(f"  {key}: {len(issue_defs)} issues, {len(milestone_defs)} milestones, {len(sprint_defs)} sprints, SLA policies")
    return project, True


print("Seeding 8 additional projects...")

seed_project(
    "WEB", "Marketing Website", "Public marketing site, blog, and pricing pages.",
    milestone_defs=[
        ("relaunch", "Site relaunch", "New design system and CMS migration.", 12),
        ("seo", "SEO overhaul", "Fix crawl issues and improve core web vitals.", -2),
    ],
    sprint_defs=[
        ("s1", "Sprint 1", "CMS migration groundwork", -7, 7, models.SprintStatus.active),
        ("s2", "Sprint 2", "Pricing page redesign", 7, 21, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "Pricing page CTA button not clickable on mobile Safari", "The 'Start free trial' button has a zero-height touch target on iOS Safari.", models.Status.open, models.Priority.critical, models.IssueType.bug, sara, marco, ["frontend", "mobile", "safari"], "relaunch", "s1", -1, "Likely a CSS flex-basis collapse on small viewports.", "high", None, [(marco, "Reproduced on iPhone 13, Safari 17.", 1)], [("Reproduce on device", True), ("Patch CSS", False)]),
        (2, "Blog RSS feed returns malformed XML", "Feed validator flags unescaped ampersands in post titles.", models.Status.in_progress, models.Priority.medium, models.IssueType.bug, nina, tom, ["backend", "content"], None, "s1", 5, "", "", None, [], []),
        (3, "Add dark mode toggle to site header", "Marketing site should respect system theme and allow manual override.", models.Status.open, models.Priority.low, models.IssueType.feature, sara, None, ["frontend", "design"], "relaunch", "s2", 20, "", "", None, [], []),
        (4, "Core Web Vitals: LCP regressed after hero video added", "Largest Contentful Paint jumped from 1.8s to 4.2s on the homepage.", models.Status.resolved, models.Priority.high, models.IssueType.bug, admin, tom, ["performance", "seo"], "seo", None, None, "", "", None, [(tom, "Lazy-loaded the video and added a static poster frame.", 3)], []),
        (5, "404 page has broken navigation links", "Footer links on the custom 404 page point to old URL structure.", models.Status.closed, models.Priority.low, models.IssueType.bug, marco, marco, ["frontend"], None, None, None, "", "", None, [], []),
        (6, "Evaluate headless CMS options for relaunch", "Compare Contentful, Sanity, and Strapi for the new site architecture.", models.Status.open, models.Priority.medium, models.IssueType.question, admin, None, ["research", "cms"], "relaunch", None, 15, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 6),
        ("High response", models.Priority.high, 24),
        ("Medium response", models.Priority.medium, 72),
        ("Low response", models.Priority.low, 168),
    ],
)

seed_project(
    "API", "Public API Platform", "Developer-facing REST API and SDKs.",
    milestone_defs=[
        ("v2", "API v2 launch", "Ship the versioned v2 endpoints with breaking changes.", 18),
        ("docs", "Docs revamp", "Rebuild developer docs with interactive examples.", -5),
    ],
    sprint_defs=[
        ("s1", "Sprint 9", "Rate limiting rollout", -5, 9, models.SprintStatus.active),
        ("s2", "Sprint 10", "Webhook reliability", 9, 23, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "Rate limit headers missing on 429 responses", "Clients can't tell how long to back off since Retry-After is absent.", models.Status.open, models.Priority.high, models.IssueType.bug, devon, tom, ["backend", "api"], "v2", "s1", 3, "Rate limiter middleware likely skips header injection on the error path.", "medium", None, [(tom, "Confirmed: only the success path sets headers.", 1)], [("Add Retry-After header", False), ("Add regression test", False)]),
        (2, "Webhook retries not using exponential backoff", "Failed webhook deliveries retry at a fixed 30s interval, hammering downstream services.", models.Status.in_progress, models.Priority.critical, models.IssueType.bug, admin, devon, ["backend", "webhooks"], "docs", "s2", -1, "", "", None, [], []),
        (3, "Add idempotency key support to POST endpoints", "Let clients safely retry writes without creating duplicates.", models.Status.open, models.Priority.high, models.IssueType.feature, nina, tom, ["api", "reliability"], "v2", "s1", 10, "", "", None, [], []),
        (4, "SDK: Python client leaks connections under load", "Long-running processes using the SDK slowly exhaust the connection pool.", models.Status.resolved, models.Priority.high, models.IssueType.bug, priya, priya, ["sdk", "python"], None, None, None, "", "", None, [(priya, "Fixed by using a shared session with proper context management.", 4)], []),
        (5, "API docs: auth example uses deprecated endpoint", "The quickstart guide still references /v1/auth/token instead of /v2/oauth/token.", models.Status.closed, models.Priority.low, models.IssueType.bug, nina, nina, ["docs"], "docs", None, None, "", "", None, [], []),
        (6, "GraphQL gateway returns 500 on nested fragment queries", "Deeply nested fragments crash the resolver with a stack overflow past depth 8.", models.Status.open, models.Priority.critical, models.IssueType.bug, devon, tom, ["backend", "graphql"], "v2", "s2", -2, "Likely unbounded recursion in fragment resolution.", "high", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 2),
        ("High response", models.Priority.high, 8),
        ("Medium response", models.Priority.medium, 24),
        ("Low response", models.Priority.low, 96),
    ],
)

seed_project(
    "CRM", "Sales CRM", "Internal tool for managing leads, deals, and pipelines.",
    milestone_defs=[
        ("pipeline", "Pipeline v2", "Rebuild the deal pipeline with custom stages.", 14),
        ("import", "Bulk import", "CSV import for leads and contacts.", -4),
    ],
    sprint_defs=[
        ("s1", "Sprint 5", "Pipeline stage editor", -3, 11, models.SprintStatus.active),
        ("s2", "Sprint 6", "Import/export tooling", 11, 25, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "Deal stage drag-and-drop loses data on fast drops", "Rapidly dragging a deal card between columns sometimes reverts to the original stage.", models.Status.open, models.Priority.high, models.IssueType.bug, nina, marco, ["frontend", "pipeline"], "pipeline", "s1", 4, "Likely a race between the optimistic UI update and the server response.", "medium", None, [(marco, "Repro'd by dragging 3 cards in under 2 seconds.", 2)], [("Reproduce reliably", True), ("Add debounce or lock", False)]),
        (2, "CSV import fails silently on duplicate emails", "Rows with emails already in the system are dropped with no error shown to the user.", models.Status.in_progress, models.Priority.critical, models.IssueType.bug, admin, tom, ["backend", "import"], "import", "s2", -1, "", "", None, [], []),
        (3, "Add custom fields to lead records", "Sales wants to track industry-specific fields per lead.", models.Status.open, models.Priority.medium, models.IssueType.feature, nina, None, ["backend", "leads"], "pipeline", None, 22, "", "", None, [], []),
        (4, "Deal value totals don't account for multi-currency", "Pipeline summary sums raw values without converting currencies.", models.Status.resolved, models.Priority.high, models.IssueType.bug, priya, priya, ["backend", "i18n"], None, None, None, "", "", None, [(priya, "Added conversion using daily exchange rates at read time.", 5)], []),
        (5, "Lead detail page: activity timeline out of order", "Comments and status changes sometimes show in the wrong chronological order.", models.Status.closed, models.Priority.low, models.IssueType.bug, marco, marco, ["frontend"], None, None, None, "", "", None, [], []),
        (6, "Evaluate Salesforce data migration path", "Scope what it takes to import 3 years of historical Salesforce data.", models.Status.open, models.Priority.medium, models.IssueType.question, admin, None, ["research", "migration"], "import", None, 18, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 4),
        ("High response", models.Priority.high, 24),
        ("Medium response", models.Priority.medium, 72),
        ("Low response", models.Priority.low, 168),
    ],
)

seed_project(
    "HR", "HR Onboarding Portal", "New-hire onboarding, document collection, and IT provisioning.",
    milestone_defs=[
        ("selfserve", "Self-serve onboarding", "Let new hires complete paperwork without HR intervention.", 16),
        ("compliance", "Compliance audit fixes", "Address gaps found in the Q2 compliance review.", -6),
    ],
    sprint_defs=[
        ("s1", "Sprint 3", "Document e-signature flow", -4, 10, models.SprintStatus.active),
        ("s2", "Sprint 4", "IT provisioning automation", 10, 24, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "E-signature step doesn't save progress on browser refresh", "New hires lose all entered data if they accidentally refresh mid-form.", models.Status.open, models.Priority.critical, models.IssueType.bug, sara, marco, ["frontend", "forms"], "selfserve", "s1", -1, "Form state is held only in React state, not persisted.", "high", None, [(marco, "Confirmed - no localStorage or server-side draft save.", 1)], [("Add autosave", False), ("Add draft recovery banner", False)]),
        (2, "IT provisioning ticket not auto-created for contractors", "Only full-time hire onboarding triggers the IT ticket webhook.", models.Status.in_progress, models.Priority.high, models.IssueType.bug, admin, devon, ["backend", "automation"], "compliance", "s2", 3, "", "", None, [], []),
        (3, "Add multi-language support for onboarding forms", "International hires need forms in their local language.", models.Status.open, models.Priority.medium, models.IssueType.feature, nina, None, ["frontend", "i18n"], "selfserve", None, 25, "", "", None, [], []),
        (4, "I-9 document upload rejects valid PDFs over 5MB", "Scanned passport copies from some phones exceed the silent size limit.", models.Status.resolved, models.Priority.high, models.IssueType.bug, sara, tom, ["backend", "compliance"], "compliance", None, None, "", "", None, [(tom, "Raised the limit to 15MB and added a clearer error message.", 4)], []),
        (5, "Welcome email template has broken logo image", "The company logo shows as a broken image icon in Outlook.", models.Status.closed, models.Priority.low, models.IssueType.bug, nina, nina, ["email"], None, None, None, "", "", None, [], []),
        (6, "Audit trail missing for offboarding document deletions", "Compliance flagged that deleted employee documents leave no record.", models.Status.open, models.Priority.high, models.IssueType.bug, admin, devon, ["backend", "compliance", "security"], "compliance", "s1", -3, "Deletion endpoint bypasses the audit log middleware used elsewhere.", "high", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 4),
        ("High response", models.Priority.high, 24),
        ("Medium response", models.Priority.medium, 72),
        ("Low response", models.Priority.low, 168),
    ],
)

seed_project(
    "ANLYT", "Analytics Dashboard", "Internal BI dashboard for product and revenue metrics.",
    milestone_defs=[
        ("realtime", "Real-time metrics", "Move from nightly batch to streaming updates.", 20),
        ("perf", "Query performance", "Cut dashboard load times under 2s.", -3),
    ],
    sprint_defs=[
        ("s1", "Sprint 11", "Streaming pipeline groundwork", -6, 8, models.SprintStatus.active),
        ("s2", "Sprint 12", "Dashboard caching layer", 8, 22, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "Revenue chart shows negative values after refund spike", "A batch of refunds caused the daily revenue line to dip below zero, which shouldn't be possible with current aggregation.", models.Status.open, models.Priority.critical, models.IssueType.bug, admin, priya, ["backend", "data"], "perf", "s1", -1, "Refunds are likely being double-subtracted in the aggregation query.", "high", None, [(priya, "Confirmed - refund events are counted in both the raw and net revenue CTEs.", 1)], [("Reproduce with sample data", True), ("Fix aggregation query", False), ("Backfill affected dates", False)]),
        (2, "Dashboard takes 8+ seconds to load on the executive summary tab", "Query performance target is under 2s; the exec tab joins 6 tables without proper indexing.", models.Status.in_progress, models.Priority.high, models.IssueType.bug, nina, tom, ["backend", "performance"], "perf", "s2", 6, "", "", None, [], []),
        (3, "Add cohort retention chart", "Product wants a standard 12-week cohort retention curve.", models.Status.open, models.Priority.medium, models.IssueType.feature, nina, None, ["frontend", "analytics"], "realtime", None, 28, "", "", None, [], []),
        (4, "Export to CSV truncates at 10,000 rows silently", "Large exports cut off with no warning, leading to incomplete reports.", models.Status.resolved, models.Priority.high, models.IssueType.bug, admin, tom, ["backend"], None, None, None, "", "", None, [(tom, "Added streaming export and a row-count warning banner.", 5)], []),
        (5, "Chart tooltip text unreadable in dark mode", "Low contrast gray text on a dark gray tooltip background.", models.Status.closed, models.Priority.low, models.IssueType.bug, sara, sara, ["frontend", "design"], None, None, None, "", "", None, [], []),
        (6, "Evaluate ClickHouse vs BigQuery for streaming layer", "Compare cost and latency for the real-time metrics milestone.", models.Status.open, models.Priority.medium, models.IssueType.question, admin, None, ["research", "infra"], "realtime", "s1", 15, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 4),
        ("High response", models.Priority.high, 24),
        ("Medium response", models.Priority.medium, 72),
        ("Low response", models.Priority.low, 168),
    ],
)

seed_project(
    "SUPP", "Customer Support Portal", "Ticketing and self-serve help center for end customers.",
    milestone_defs=[
        ("selfserve2", "Self-serve deflection", "Reduce ticket volume via better help articles and a chatbot.", 12),
        ("csat", "CSAT improvement", "Address root causes behind falling satisfaction scores.", -7),
    ],
    sprint_defs=[
        ("s1", "Sprint 20", "Chatbot handoff flow", -2, 12, models.SprintStatus.active),
        ("s2", "Sprint 21", "Help article search", 12, 26, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "Chatbot hands off to human agent without conversation context", "Agents receive escalated chats with no visibility into what the bot already discussed.", models.Status.open, models.Priority.critical, models.IssueType.bug, lena, devon, ["backend", "chatbot"], "csat", "s1", -1, "Handoff payload is missing the transcript field entirely.", "high", None, [(devon, "Confirmed - handoff webhook only sends the ticket ID, not history.", 1)], [("Add transcript to handoff payload", False), ("Display in agent UI", False)]),
        (2, "Help article search returns irrelevant results for common queries", "Searching 'reset password' surfaces unrelated billing articles first.", models.Status.in_progress, models.Priority.high, models.IssueType.bug, nina, tom, ["backend", "search"], "selfserve2", "s2", 8, "", "", None, [], []),
        (3, "Add satisfaction survey after ticket resolution", "Send a 1-question CSAT survey automatically when a ticket closes.", models.Status.open, models.Priority.medium, models.IssueType.feature, nina, None, ["backend", "csat"], "csat", None, 20, "", "", None, [], []),
        (4, "Ticket attachments over 10MB fail with no error message", "Users see a spinning upload icon forever instead of a size limit error.", models.Status.resolved, models.Priority.high, models.IssueType.bug, lena, marco, ["frontend"], None, None, None, "", "", None, [(marco, "Added client-side size validation with a clear error toast.", 3)], []),
        (5, "Agent dashboard: unread badge count sometimes stuck at 1", "Badge doesn't clear even after all tickets in a queue are read.", models.Status.closed, models.Priority.low, models.IssueType.bug, lena, lena, ["frontend"], None, None, None, "", "", None, [], []),
        (6, "Investigate root cause of CSAT drop in EU region", "EU satisfaction scores fell 15% over the last month; unclear if it's product, support, or timezone coverage.", models.Status.open, models.Priority.high, models.IssueType.question, admin, None, ["research", "csat"], "csat", "s1", -2, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 2),
        ("High response", models.Priority.high, 12),
        ("Medium response", models.Priority.medium, 48),
        ("Low response", models.Priority.low, 120),
    ],
)

seed_project(
    "IOT", "IoT Fleet Management", "Device provisioning, telemetry, and firmware updates for connected hardware.",
    milestone_defs=[
        ("ota", "OTA rollout v3", "Safer staged firmware rollouts with automatic rollback.", 24),
        ("telemetry", "Telemetry pipeline fixes", "Address data loss during high-traffic windows.", -8),
    ],
    sprint_defs=[
        ("s1", "Sprint 15", "Staged rollout groundwork", -8, 6, models.SprintStatus.active),
        ("s2", "Sprint 16", "Telemetry buffering", 6, 20, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "Firmware rollback doesn't trigger on repeated boot failures", "Devices stuck in a boot loop after a bad OTA update never fall back to the last known-good firmware.", models.Status.open, models.Priority.critical, models.IssueType.bug, devon, raj, ["firmware", "reliability"], "ota", "s1", -2, "Rollback watchdog counter likely resets on each reboot instead of persisting across cycles.", "high", None, [(raj, "Confirmed on 3 test devices - watchdog counter resets to 0 every boot.", 1)], [("Reproduce boot loop", True), ("Fix watchdog counter persistence", False), ("Test rollback on hardware", False)]),
        (2, "Telemetry data dropped during regional traffic spikes", "Ingestion pipeline silently drops messages when queue depth exceeds threshold instead of backpressuring.", models.Status.in_progress, models.Priority.high, models.IssueType.bug, admin, tom, ["backend", "telemetry"], "telemetry", "s2", 9, "", "", None, [], []),
        (3, "Add per-device firmware version dashboard", "Fleet ops wants a live view of which firmware version each device is running.", models.Status.open, models.Priority.medium, models.IssueType.feature, nina, None, ["frontend", "fleet"], "ota", None, 26, "", "", None, [], []),
        (4, "Device provisioning QR code expires too quickly", "5-minute expiry window is too short for warehouse batch provisioning workflows.", models.Status.resolved, models.Priority.medium, models.IssueType.bug, devon, devon, ["backend", "provisioning"], None, None, None, "", "", None, [(devon, "Extended expiry to 30 minutes and added a refresh option.", 6)], []),
        (5, "Device status icon shows 'online' for up to 2 minutes after disconnect", "Heartbeat timeout is too generous, giving a false sense of connectivity.", models.Status.closed, models.Priority.low, models.IssueType.bug, raj, raj, ["frontend"], None, None, None, "", "", None, [], []),
        (6, "Evaluate MQTT vs CoAP for next-gen device protocol", "Compare power consumption and reliability tradeoffs for battery-powered sensors.", models.Status.open, models.Priority.medium, models.IssueType.question, admin, None, ["research", "firmware"], "telemetry", None, 17, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 2),
        ("High response", models.Priority.high, 12),
        ("Medium response", models.Priority.medium, 48),
        ("Low response", models.Priority.low, 168),
    ],
)

seed_project(
    "GAME", "Mobile Game Backend", "Live-ops backend for a mobile game: matchmaking, economy, and events.",
    milestone_defs=[
        ("season", "Season 4 launch", "New battle pass, ranked ladder reset, and cosmetics.", 9),
        ("antifraud", "Anti-fraud pass", "Close exploits found by the economy team.", -5),
    ],
    sprint_defs=[
        ("s1", "Sprint 30", "Matchmaking rebalance", -3, 11, models.SprintStatus.active),
        ("s2", "Sprint 31", "Season 4 content", 11, 25, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "In-game currency duplication exploit via failed purchase retry", "Retrying a timed-out purchase can credit currency twice without deducting real money twice.", models.Status.open, models.Priority.critical, models.IssueType.bug, admin, priya, ["backend", "economy", "security"], "antifraud", "s1", -3, "Purchase confirmation isn't idempotent - retries re-trigger the currency grant.", "high", None, [(priya, "Confirmed exploit path, currently rate-limiting retries as a stopgap.", 1)], [("Add idempotency key to purchase flow", False), ("Audit affected accounts", False), ("Deploy permanent fix", False)]),
        (2, "Matchmaking puts new players against ranked veterans", "Skill-based matchmaking isn't weighting account age, causing lopsided early-game matches.", models.Status.in_progress, models.Priority.high, models.IssueType.bug, nina, tom, ["backend", "matchmaking"], "season", "s1", 4, "", "", None, [], []),
        (3, "Add battle pass progress notifications", "Push a notification when a player is 1 tier away from a reward.", models.Status.open, models.Priority.medium, models.IssueType.feature, nina, None, ["backend", "engagement"], "season", "s2", 12, "", "", None, [], []),
        (4, "Leaderboard cache serves stale ranks for up to 10 minutes", "Players who just won a ranked match don't see their updated position promptly.", models.Status.resolved, models.Priority.medium, models.IssueType.bug, admin, tom, ["backend", "performance"], None, None, None, "", "", None, [(tom, "Reduced cache TTL and added a manual invalidation on match end.", 4)], []),
        (5, "Cosmetic preview renders wrong character skeleton", "New skin preview shows the base model instead of the purchased skin mesh.", models.Status.closed, models.Priority.low, models.IssueType.bug, marco, marco, ["frontend", "art"], None, None, None, "", "", None, [], []),
        (6, "Evaluate server regions for Season 4 launch traffic", "Model expected concurrent players per region to plan capacity ahead of launch.", models.Status.open, models.Priority.high, models.IssueType.question, admin, None, ["research", "infra"], "season", None, 8, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 1),
        ("High response", models.Priority.high, 6),
        ("Medium response", models.Priority.medium, 24),
        ("Low response", models.Priority.low, 96),
    ],
)

seed_project(
    "INFRA", "Platform Infrastructure", "Core infra: CI/CD, observability, and cloud cost management.",
    milestone_defs=[
        ("costs", "Cloud cost reduction", "Cut monthly spend by 20% through rightsizing and reserved capacity.", 30),
        ("observability", "Observability upgrade", "Unify logs, metrics, and traces into one pane of glass.", -1),
    ],
    sprint_defs=[
        ("s1", "Sprint 40", "Rightsizing audit", -10, 4, models.SprintStatus.active),
        ("s2", "Sprint 41", "Tracing rollout", 4, 18, models.SprintStatus.planned),
    ],
    issue_defs=[
        (1, "CI pipeline randomly hangs on the integration test stage", "Roughly 1 in 15 runs hangs indefinitely rather than failing, requiring manual cancellation.", models.Status.open, models.Priority.critical, models.IssueType.bug, admin, devon, ["ci/cd", "infra"], "observability", "s1", -2, "Suspected deadlock between the test DB container and a lingering connection pool.", "medium", None, [(devon, "Captured a thread dump during a hang, investigating the connection pool lock.", 1)], [("Capture thread dump during hang", True), ("Identify deadlock source", False), ("Add timeout safeguard", False)]),
        (2, "Staging environment costs 3x more than expected", "Unused staging resources aren't being scaled down outside business hours.", models.Status.in_progress, models.Priority.high, models.IssueType.bug, admin, devon, ["infra", "cost"], "costs", "s1", 2, "", "", None, [], []),
        (3, "Add distributed tracing to the checkout service", "Currently only logs exist; need request-level tracing to debug cross-service latency.", models.Status.open, models.Priority.medium, models.IssueType.feature, admin, None, ["observability", "backend"], "observability", "s2", 14, "", "", None, [], []),
        (4, "Alerting fires duplicate pages for the same incident", "PagerDuty sends 3-4 separate pages for a single downstream outage.", models.Status.resolved, models.Priority.high, models.IssueType.bug, devon, devon, ["observability", "alerting"], None, None, None, "", "", None, [(devon, "Added alert grouping rules keyed by root-cause service.", 5)], []),
        (5, "Terraform plan output includes secrets in plaintext", "Sensitive variable values appear unmasked in CI logs during plan steps.", models.Status.closed, models.Priority.critical, models.IssueType.bug, admin, devon, ["infra", "security"], None, None, None, "", "", None, [(devon, "Marked all secret variables as sensitive in Terraform config.", 8)], []),
        (6, "Evaluate reserved instance vs spot pricing for batch jobs", "Batch processing workloads may be a good fit for spot pricing given their fault tolerance.", models.Status.open, models.Priority.medium, models.IssueType.question, admin, None, ["research", "cost"], "costs", None, 25, "", "", None, [], []),
    ],
    sla_defs=[
        ("Critical response", models.Priority.critical, 1),
        ("High response", models.Priority.high, 4),
        ("Medium response", models.Priority.medium, 24),
        ("Low response", models.Priority.low, 72),
    ],
)

print("Adding extra sprints...")
get_or_create_sprint(shop, "Sprint 14", "Design system rollout", now + timedelta(days=14), now + timedelta(days=28), models.SprintStatus.planned)
get_or_create_sprint(shop, "Sprint 15", "Performance pass", now + timedelta(days=28), now + timedelta(days=42), models.SprintStatus.planned)
get_or_create_sprint(mobl, "Sprint 8", "Push notification overhaul", now + timedelta(days=7), now + timedelta(days=21), models.SprintStatus.planned)
print("  Added 3 sprints (SHOP x2, MOBL x1)")

db.close()
print("\nDone. Log in as any of these to explore different views:")
print("  admin        / admin123    (admin)")
print("  priya_dev    / password123 (backend)")
print("  marco_fe     / password123 (frontend)")
print("  lena_qa      / password123 (QA)")
print("  raj_mobile   / password123 (mobile)")
print("  devon_devops / password123 (devops)")
print("  sara_design  / password123 (design)")
print("  tom_backend  / password123 (backend)")
print("  nina_pm      / password123 (PM)")
print("  alex_fe2     / password123 (frontend)")
