const API = "";

function saveAuth(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
}
function loadAuth() {
  const token = localStorage.getItem("token");
  const user = localStorage.getItem("user");
  return { token, user: user ? JSON.parse(user) : null };
}
function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

const state = {
  token: null,
  user: null,
  view: "landing",
  projects: [],
  currentProjectId: null,
  issues: [],
  issuesView: "list",
  currentIssue: null,
  comments: [],
  duplicates: [],
  stats: null,
  users: [],
  milestones: [],
  sprints: [],
  filters: { status: "", priority: "", search: "", milestone_id: "", sprint_id: "" },
  chatMessages: [],
  chatWidgetOpen: false,
  chatSending: false,
  modal: null,
  loading: false,
  errorMsg: "",
  theme: "light",
  adminStats: null,
  adminUsers: [],
  adminProjects: [],
  adminIssues: [],
  weeklyReport: null,
  workload: [],
  assigneeSuggestion: null,
  sprintRisk: {},
  activitySummary: null,
  copilotOpen: {},
  copilotChats: {},
  copilotLoading: {},
  timeLogs: [],
  checklist: [],
  notifications: [],
  notifDropdownOpen: false,
  stackTraceLoading: false,
  stackTraceResult: null,
  sprintPlanLoading: null,
  sprintPlans: {},
  attachments: [],
  profiles: [],
  myProfile: null,
  assigneeComparison: null,
  assigneeComparisonLoading: false,
  slaPolicies: [],
  slaBreaches: [],
  issueMetrics: null,
  issueMetricsLoading: false,
};

async function apiFetch(path, opts = {}) {
  const headers = Object.assign(
    { "Content-Type": "application/json" },
    opts.headers || {}
  );
  if (state.token) headers["Authorization"] = "Bearer " + state.token;

  const res = await fetch(API + path, Object.assign({}, opts, { headers }));
  if (res.status === 401) {
    clearAuth();
    state.token = null;
    state.user = null;
    state.view = "landing";
    render();
    throw new Error("Session expired, please log in again");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function init() {
  applyTheme(localStorage.getItem("theme") || "light");
  const { token, user } = loadAuth();
  if (token) {
    state.token = token;
    state.user = user;
    state.view = "dashboard";
    loadProjects().then(() => {
      if (state.projects.length) state.currentProjectId = state.projects[0].id;
      refreshAll();
    });
    loadUnreadNotifCount();
  }
  render();
}

async function refreshAll() {
  await Promise.all([loadIssues(), loadStats(), loadUsers(), loadMilestones(), loadSprints()]);
  render();
}

async function loadProjects() {
  state.projects = await apiFetch("/api/projects");
}
async function loadUsers() {
  try {
    state.users = await apiFetch("/api/auth/users");
  } catch (e) {}
}
async function loadIssues() {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("project_id", state.currentProjectId);
  if (state.filters.status) params.set("status", state.filters.status);
  if (state.filters.priority) params.set("priority", state.filters.priority);
  if (state.filters.search) params.set("search", state.filters.search);
  if (state.filters.milestone_id) params.set("milestone_id", state.filters.milestone_id);
  if (state.filters.sprint_id) params.set("sprint_id", state.filters.sprint_id);
  state.issues = await apiFetch("/api/issues?" + params.toString());
}
async function loadStats() {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("project_id", state.currentProjectId);
  state.stats = await apiFetch("/api/dashboard/stats?" + params.toString());
}
async function loadMilestones() {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("project_id", state.currentProjectId);
  state.milestones = await apiFetch("/api/milestones?" + params.toString());
}
async function loadSprints() {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("project_id", state.currentProjectId);
  state.sprints = await apiFetch("/api/sprints?" + params.toString());
}
async function openIssue(id) {
  state.currentIssue = await apiFetch("/api/issues/" + id);
  state.comments = await apiFetch("/api/issues/" + id + "/comments");
  state.timeLogs = await apiFetch("/api/issues/" + id + "/timelogs");
  state.checklist = await apiFetch("/api/issues/" + id + "/checklist");
  state.stackTraceResult = null;
  state.attachments = await apiFetch("/api/issues/" + id + "/attachments");
  state.duplicates = [];
  state.view = "issueDetail";
  render();
}

async function loadAdmin() {
  const [stats, users, projects, issues] = await Promise.all([
    apiFetch("/api/admin/stats"),
    apiFetch("/api/admin/users"),
    apiFetch("/api/admin/projects"),
    apiFetch("/api/admin/issues"),
  ]);
  state.adminStats = stats;
  state.adminUsers = users;
  state.adminProjects = projects;
  state.adminIssues = issues;
}

async function changeUserRole(id, role) {
  try {
    await apiFetch("/api/admin/users/" + id + "/role", {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
    await loadAdmin();
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteUserAdmin(id, username) {
  if (!confirm("Delete user \"" + username + "\"? This cannot be undone.")) return;
  try {
    await apiFetch("/api/admin/users/" + id, { method: "DELETE" });
    await loadAdmin();
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteProjectAdmin(id, name) {
  if (!confirm("Delete project \"" + name + "\" and ALL its issues? This cannot be undone.")) return;
  try {
    await apiFetch("/api/admin/projects/" + id, { method: "DELETE" });
    await loadAdmin();
    await loadProjects();
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteIssueAdmin(id, title) {
  if (!confirm("Delete issue \"" + title + "\"? This cannot be undone.")) return;
  try {
    await apiFetch("/api/admin/issues/" + id, { method: "DELETE" });
    await loadAdmin();
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function doLogin(username, password) {
  state.errorMsg = "";
  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    state.token = data.access_token;
    state.user = data.user;
    saveAuth(state.token, state.user);
    state.view = "dashboard";
    await loadProjects();
    if (state.projects.length) state.currentProjectId = state.projects[0].id;
    await refreshAll();
  } catch (e) {
    state.errorMsg = e.message;
    render();
  }
}

async function doRegister(username, email, password) {
  state.errorMsg = "";
  try {
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
    state.token = data.access_token;
    state.user = data.user;
    saveAuth(state.token, state.user);
    state.view = "dashboard";
    await loadProjects();
    if (state.projects.length) state.currentProjectId = state.projects[0].id;
    await refreshAll();
  } catch (e) {
    state.errorMsg = e.message;
    render();
  }
}

function doLogout() {
  clearAuth();
  state.token = null;
  state.user = null;
  state.view = "landing";
  render();
}

async function createProject(key, name, description) {
  try {
    await apiFetch("/api/projects", {
      method: "POST",
      body: JSON.stringify({ key, name, description }),
    });
    await loadProjects();
    state.currentProjectId = state.projects[0].id;
    state.modal = null;
    await refreshAll();
  } catch (e) {
    alert(e.message);
  }
}

async function createIssue(payload) {
  try {
    await apiFetch("/api/issues", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.modal = null;
    await refreshAll();
  } catch (e) {
    alert(e.message);
  }
}

async function updateIssueField(id, field, value) {
  await apiFetch("/api/issues/" + id, {
    method: "PATCH",
    body: JSON.stringify({ [field]: value }),
  });
  await openIssue(id);
  await refreshAll();
}

async function postComment(id, body) {
  if (!body.trim()) return;
  await apiFetch("/api/issues/" + id + "/comments", {
    method: "POST",
    body: JSON.stringify({ body }),
  });
  await openIssue(id);
}

async function askAiSuggest(id) {
  state.loading = true;
  render();
  try {
    await apiFetch("/api/issues/" + id + "/ai-suggest", { method: "POST" });
    await openIssue(id);
  } catch (e) {
    alert(e.message);
  }
  state.loading = false;
  render();
}

async function askAiCodeFix(id) {
  state.loading = true;
  render();
  try {
    await apiFetch("/api/issues/" + id + "/ai-fix-suggestion", { method: "POST" });
    await openIssue(id);
  } catch (e) {
    alert(e.message);
  }
  state.loading = false;
  render();
}

async function checkDuplicates(id) {
  state.loading = true;
  render();
  try {
    state.duplicates = await apiFetch("/api/issues/" + id + "/find-duplicates", {
      method: "POST",
    });
  } catch (e) {
    alert(e.message);
  }
  state.loading = false;
  render();
}

async function checkLiveDuplicates() {
  const titleEl = document.getElementById("ni-title");
  const descEl = document.getElementById("ni-desc");
  const resultEl = document.getElementById("ni-dup-results");
  if (!titleEl || !resultEl) return;
  const title = titleEl.value.trim();
  if (title.length < 5 || !state.currentProjectId) {
    resultEl.innerHTML = "";
    return;
  }
  resultEl.innerHTML = '<div class="dup-checking"><span class="spin"></span> Checking for duplicates...</div>';
  try {
    const results = await apiFetch("/api/issues/live-duplicate-check", {
      method: "POST",
      body: JSON.stringify({
        project_id: state.currentProjectId,
        title: title,
        description: descEl ? descEl.value : "",
      }),
    });
    if (results.length) {
      resultEl.innerHTML =
        '<div class="dup-live-banner"><b>Possible duplicates:</b><br>' +
        results.map(d => `#${d.number} "${escapeHtml(d.title)}" - ${d.confidence} confidence`).join("<br>") +
        "</div>";
    } else {
      resultEl.innerHTML = "";
    }
  } catch (e) {
    resultEl.innerHTML = "";
  }
}

async function setProject(id) {
  state.currentProjectId = Number(id);
  await refreshAll();
}

async function setView(view) {
  state.view = view;
  if (view === "home") await loadStats();
  if (view === "dashboard") await loadStats();
  if (view === "issues") await loadIssues();
  if (view === "admin") await loadAdmin();
  if (view === "milestones") await loadMilestones();
  if (view === "sprints") await loadSprints();
  if (view === "workload") await loadWorkload();
  if (view === "reports") { state.weeklyReport = null; }
  if (view === "profiles") { state.profiles = await apiFetch("/api/profiles"); }
  if (view === "sla") {
    const params = new URLSearchParams();
    if (state.currentProjectId) params.set("project_id", state.currentProjectId);
    state.slaPolicies = await apiFetch("/api/sla/policies?" + params.toString());
    state.slaBreaches = await apiFetch("/api/sla/breaches?" + params.toString());
  }
  render();
}

async function applyFilters() {
  await loadIssues();
  render();
}

async function handleKanbanDrop(event, newStatus) {
  event.preventDefault();
  const id = event.dataTransfer.getData("text/plain");
  if (!id) return;
  try {
    await apiFetch("/api/issues/" + id, {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus }),
    });
    await loadIssues();
    await loadStats();
    render();
  } catch (e) {
    alert(e.message);
  }
}

function badgeClass(status) {
  return "badge badge-" + status;
}
function fmtDate(d) {
  return new Date(d).toLocaleString();
}
function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function renderCommentBody(body) {
  const text = body || "";
  const parts = text.split(/```(\w*)\n?([\s\S]*?)```/g);
  let html = "";
  for (let i = 0; i < parts.length; i += 3) {
    const plain = parts[i];
    if (plain) html += escapeHtml(plain).replace(/\n/g, "<br>");
    const code = parts[i + 2];
    if (code !== undefined) {
      html += `<pre class="code-block">${escapeHtml(code)}</pre>`;
    }
  }
  return html;
}

function sidebarHtml() {
  const isAdmin = state.user && state.user.role === "admin";
  return `
    <div class="sidebar">
      <div class="brand"><span class="mark"></span>Triagey</div>
      <div class="nav-section">
        <div class="nav-label">Workspace</div>
        <div class="nav-item ${state.view === "home" ? "active" : ""}" onclick="setView('home')">Home</div>
        <div class="nav-item ${state.view === "dashboard" ? "active" : ""}" onclick="setView('dashboard')">Dashboard</div>
        <div class="nav-item ${state.view === "issues" || state.view === "issueDetail" ? "active" : ""}" onclick="setView('issues')">Bugs &amp; Kanban</div>
        <div class="nav-item ${state.view === "milestones" ? "active" : ""}" onclick="setView('milestones')">Milestones</div>
        <div class="nav-item ${state.view === "sprints" ? "active" : ""}" onclick="setView('sprints')">Sprints</div>
        <div class="nav-item ${state.view === "workload" ? "active" : ""}" onclick="setView('workload')">Workload</div>
        <div class="nav-item ${state.view === "reports" ? "active" : ""}" onclick="setView('reports')">Weekly Report</div>
        <div class="nav-item ${state.view === "profiles" ? "active" : ""}" onclick="setView('profiles')">Team Profiles</div>
        <div class="nav-item ${state.view === "sla" ? "active" : ""}" onclick="setView('sla')">SLA</div>
        <div class="nav-item ${state.view === "projects" ? "active" : ""}" onclick="setView('projects')">Projects</div>
        ${isAdmin ? `<div class="nav-item ${state.view === "admin" ? "active" : ""}" onclick="setView('admin')">Admin</div>` : ""}
      </div>
      <div class="nav-section">
        <div class="nav-label">Info</div>
        <div class="nav-item ${state.view === "about" ? "active" : ""}" onclick="setView('about')">About</div>
        <div class="nav-item ${state.view === "features" ? "active" : ""}" onclick="setView('features')">Features</div>
        <div class="nav-item ${state.view === "chat" ? "active" : ""}" onclick="setView('chat')">Chat</div>
      </div>
      <div class="nav-section">
        <div class="nav-label">Project</div>
        <select onchange="setProject(this.value)">
          ${state.projects.map(p => `<option value="${p.id}" ${p.id === state.currentProjectId ? "selected" : ""}>${escapeHtml(p.key)} - ${escapeHtml(p.name)}</option>`).join("")}
        </select>
      </div>
      <div style="margin-top:auto">
        <div class="notif-bell" onclick="toggleNotifDropdown(event)" style="margin-bottom:10px">
          &#128276; Notifications
          ${state.notifications.filter(n => !n.is_read).length > 0 ? `<span class="notif-badge">${state.notifications.filter(n => !n.is_read).length}</span>` : ""}
          ${state.notifDropdownOpen ? notifDropdownHtml() : ""}
        </div>
        <div class="subtle">Signed in as <b>${escapeHtml(state.user?.username || "")}</b> ${isAdmin ? '<span class="role-badge admin">admin</span>' : ""}</div>
        <button class="btn btn-ghost" style="margin-top:8px;width:100%" onclick="toggleTheme()">${state.theme === "dark" ? "Light mode" : "Dark mode"}</button>
        <button class="btn btn-ghost" style="margin-top:8px;width:100%" onclick="doLogout()">Log out</button>
      </div>
    </div>
  `;
}

function landingHtml() {
  return `
    <div class="landing-wrap">
      <div class="landing-nav">
        <div class="brand"><span class="mark"></span>Triagey</div>
        <div class="gap-8">
          <button class="btn btn-ghost" onclick="toggleTheme()">${state.theme === "dark" ? "Light mode" : "Dark mode"}</button>
          <button class="btn btn-ghost" onclick="state.view='login'; render()">Log in</button>
          <button class="btn btn-primary" onclick="state.view='register'; render()">Get started</button>
        </div>
      </div>
      <div class="landing-hero">
        <h1>AI-powered bug tracking &amp; issue management</h1>
        <p>Triagey helps small teams report, triage, and resolve issues faster - with AI doing the first pass on priority, duplicates, and root cause.</p>
        <button class="btn btn-primary" onclick="state.view='register'; render()">Launch workspace</button>
      </div>
      <div class="landing-features">
        <div class="landing-feature">
          <div class="icon">&#128193;</div>
          <h3>Kanban board</h3>
          <p>Drag issues between Open, In progress, Resolved, and Closed as work moves.</p>
        </div>
        <div class="landing-feature">
          <div class="icon">&#10022;</div>
          <h3>AI duplicate detection</h3>
          <p>Catch repeat reports before they pile up, live while you type or on demand.</p>
        </div>
        <div class="landing-feature">
          <div class="icon">&#128295;</div>
          <h3>AI root cause &amp; fix suggestions</h3>
          <p>Ask AI to draft a likely root cause and an illustrative code fix for any issue.</p>
        </div>
      </div>
    </div>
  `;
}

function authViewHtml() {
  if (state.view === "landing") {
    return landingHtml();
  }
  if (state.view === "register") {
    return `
      <div class="auth-wrap">
        <div class="card auth-card">
          <div class="back-link" onclick="state.view='landing'; render()">&larr; Back to home</div>
          <div class="auth-title">Create your account</div>
          <div class="subtle" style="margin-bottom:16px">First user to register becomes admin.</div>
          <div class="field"><label>Username</label><input type="text" id="reg-username"></div>
          <div class="field"><label>Email</label><input type="text" id="reg-email"></div>
          <div class="field"><label>Password</label><input type="password" id="reg-password"></div>
          <button class="btn btn-primary" style="width:100%" onclick="doRegister(document.getElementById('reg-username').value, document.getElementById('reg-email').value, document.getElementById('reg-password').value)">Create account</button>
          ${state.errorMsg ? `<div class="error-text">${escapeHtml(state.errorMsg)}</div>` : ""}
          <div class="auth-switch" onclick="state.view='login'; state.errorMsg=''; render()">Already have an account? Log in</div>
        </div>
      </div>
    `;
  }
  return `
    <div class="auth-wrap">
      <div class="card auth-card">
        <div class="back-link" onclick="state.view='landing'; render()">&larr; Back to home</div>
        <div class="auth-title">Welcome back</div>
        <div class="subtle" style="margin-bottom:16px">Log in to Triagey.</div>
        <div class="field"><label>Username</label><input type="text" id="login-username"></div>
        <div class="field"><label>Password</label><input type="password" id="login-password"></div>
        <button class="btn btn-primary" style="width:100%" onclick="doLogin(document.getElementById('login-username').value, document.getElementById('login-password').value)">Log in</button>
        ${state.errorMsg ? `<div class="error-text">${escapeHtml(state.errorMsg)}</div>` : ""}
        <div class="auth-switch" onclick="state.view='register'; state.errorMsg=''; render()">No account yet? Register</div>
      </div>
    </div>
  `;
}

function dashboardHtml() {
  const s = state.stats || { total: 0, by_status: {}, by_priority: {}, by_type: {} };
  return `
    <div class="topbar">
      <h1>Dashboard</h1>
      <button class="btn btn-primary" onclick="state.modal='newIssue'; render()">+ New issue</button>
    </div>
    <div class="stat-row">
      <div class="card stat-card"><div class="stat-num">${s.total}</div><div class="stat-label">Total issues</div></div>
      <div class="card stat-card"><div class="stat-num">${s.by_status.open || 0}</div><div class="stat-label">Open</div></div>
      <div class="card stat-card"><div class="stat-num">${s.by_status.in_progress || 0}</div><div class="stat-label">In progress</div></div>
      <div class="card stat-card"><div class="stat-num">${s.by_status.resolved || 0}</div><div class="stat-label">Resolved</div></div>
      <div class="card stat-card"><div class="stat-num" style="color:${(s.overdue_count||0) > 0 ? 'var(--danger)' : 'inherit'}">${s.overdue_count || 0}</div><div class="stat-label">Overdue</div></div>
    </div>
    <div class="breakdown">
      <div class="card">
        <h2>By priority</h2>
        ${["critical","high","medium","low"].map(p => `<div class="breakdown-row"><span>${p}</span><span>${s.by_priority[p] || 0}</span></div>`).join("")}
      </div>
      <div class="card">
        <h2>By type</h2>
        ${["bug","feature","task","question"].map(t => `<div class="breakdown-row"><span>${t}</span><span>${s.by_type[t] || 0}</span></div>`).join("")}
      </div>
      <div class="card">
        <h2>By status</h2>
        ${["open","in_progress","resolved","closed"].map(st => `<div class="breakdown-row"><span>${st}</span><span>${s.by_status[st] || 0}</span></div>`).join("")}
      </div>
    </div>
  `;
}

function issuesHtml() {
  const activeMilestone = state.filters.milestone_id ? state.milestones.find(m => m.id === Number(state.filters.milestone_id)) : null;
  const activeSprint = state.filters.sprint_id ? state.sprints.find(s => s.id === Number(state.filters.sprint_id)) : null;
  return `
    <div class="topbar">
      <h1>Bugs &amp; Kanban</h1>
      <div class="gap-8">
        <div class="view-toggle">
          <button class="${state.issuesView === "list" ? "active" : ""}" onclick="state.issuesView='list'; render()">List</button>
          <button class="${state.issuesView === "kanban" ? "active" : ""}" onclick="state.issuesView='kanban'; render()">Kanban</button>
        </div>
        <button class="btn btn-ghost" onclick="exportIssuesCsv()">Export CSV</button>
        <button class="btn btn-primary" onclick="state.modal='newIssue'; render()">+ New issue</button>
      </div>
    </div>
    ${activeMilestone ? `<div class="filter-banner">Filtered by milestone: <b>${escapeHtml(activeMilestone.title)}</b><span class="clear-filter" onclick="state.filters.milestone_id=''; applyFilters()">Clear</span></div>` : ""}
    ${activeSprint ? `<div class="filter-banner">Filtered by sprint: <b>${escapeHtml(activeSprint.name)}</b><span class="clear-filter" onclick="state.filters.sprint_id=''; applyFilters()">Clear</span></div>` : ""}
    ${state.issuesView === "list" ? `
      <div class="toolbar">
        <input type="text" placeholder="Search issues..." value="${escapeHtml(state.filters.search)}"
          oninput="state.filters.search=this.value" onkeydown="if(event.key==='Enter') applyFilters()">
        <select onchange="state.filters.status=this.value; applyFilters()">
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select onchange="state.filters.priority=this.value; applyFilters()">
          <option value="">All priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <button class="btn btn-ghost" onclick="applyFilters()">Apply</button>
      </div>
      ${state.issues.length === 0 ? `<div class="empty-state">No issues yet. Create your first one to see AI triage in action.</div>` : ""}
      ${state.issues.map(issueRowHtml).join("")}
    ` : kanbanHtml()}
  `;
}

function issueRowHtml(issue) {
  const project = state.projects.find(p => p.id === issue.project_id);
  const key = project ? project.key + "-" + issue.number : "#" + issue.number;
  return `
    <div class="issue-row" onclick="openIssue(${issue.id})">
      <div class="signal ${issue.priority}"><span></span><span></span><span></span><span></span></div>
      <div class="issue-key">${key}</div>
      <div>
        <div class="issue-title">${escapeHtml(issue.title)} ${issue.ai_summary ? `<span class="ai-marker">AI triaged</span>` : ""} ${isOverdue(issue) ? `<span class="overdue-badge">Overdue</span>` : ""}</div>
        <div class="issue-tags">${(issue.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
      </div>
      <span class="badge ${badgeClass(issue.status)}">${issue.status}</span>
      <span class="subtle">${issue.assignee ? escapeHtml(issue.assignee.username) : "Unassigned"}</span>
      <span class="subtle">${fmtDate(issue.created_at)}</span>
    </div>
  `;
}

function kanbanHtml() {
  const columns = [
    { key: "open", label: "Open" },
    { key: "in_progress", label: "In progress" },
    { key: "resolved", label: "Resolved" },
    { key: "closed", label: "Closed" },
  ];
  return `
    <div class="kanban-board">
      ${columns.map(col => {
        const colIssues = state.issues.filter(i => i.status === col.key);
        return `
          <div class="kanban-column" ondragover="event.preventDefault()" ondrop="handleKanbanDrop(event, '${col.key}')">
            <div class="kanban-column-header"><span>${col.label}</span><span>${colIssues.length}</span></div>
            ${colIssues.map(kanbanCardHtml).join("")}
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function kanbanCardHtml(issue) {
  const project = state.projects.find(p => p.id === issue.project_id);
  const key = project ? project.key + "-" + issue.number : "#" + issue.number;
  return `
    <div class="kanban-card" draggable="true" ondragstart="event.dataTransfer.setData('text/plain', '${issue.id}')" onclick="openIssue(${issue.id})">
      <span class="issue-key">${key}</span>
      <div class="kanban-card-title">${escapeHtml(issue.title)} ${isOverdue(issue) ? `<span class="overdue-badge">Overdue</span>` : ""}</div>
      <div class="signal ${issue.priority}" style="margin-top:6px"><span></span><span></span><span></span><span></span></div>
    </div>
  `;
}

function issueDetailHtml() {
  const issue = state.currentIssue;
  if (!issue) return "";
  const project = state.projects.find(p => p.id === issue.project_id);
  const key = project ? project.key + "-" + issue.number : "#" + issue.number;

  return `
    <div class="detail-header">
      <div>
        <div class="subtle">${key}</div>
        <h1>${escapeHtml(issue.title)}</h1>
      </div>
      <button class="btn btn-ghost" onclick="setView('issues')">Back to issues</button>
    </div>

    ${state.duplicates.length ? `
      <div class="duplicate-banner">
        <b>Possible duplicates found:</b><br>
        ${state.duplicates.map(d => `#${d.number} "${escapeHtml(d.title)}" - ${d.confidence} confidence: ${escapeHtml(d.reason)}`).join("<br>")}
      </div>` : ""}

    ${issue.ai_summary ? `<div class="comment ai"><b>AI summary:</b> ${escapeHtml(issue.ai_summary)} (${issue.ai_confidence} confidence)</div>` : ""}

    <div class="detail-grid">
      <div>
        <div class="card" style="margin-bottom:16px">
          <h2>Description</h2>
          <p>${escapeHtml(issue.description) || '<span class="subtle">No description</span>'}</p>
          ${issue.pr_link ? `<div style="margin-top:10px"><a href="${escapeHtml(issue.pr_link)}" target="_blank" rel="noopener">GitHub PR &#8599;</a></div>` : ""}
        </div>

        <div class="card" style="margin-bottom:16px">
          <h2>Attachments</h2>
          <div class="dropzone" id="dropzone"
            ondragover="event.preventDefault(); this.classList.add('dragover')"
            ondragleave="this.classList.remove('dragover')"
            ondrop="handleFileDrop(event, ${issue.id})"
            onclick="document.getElementById('file-input-hidden').click()">
            Drag & drop a file here, or click to browse
          </div>
          <input type="file" id="file-input-hidden" style="display:none" onchange="handleFileSelect(event, ${issue.id})">
          ${state.attachments.length === 0 ? `<div class="subtle">No attachments yet.</div>` : ""}
          ${state.attachments.map(a => `
            <div class="attachment-row">
              <a href="/api/issues/attachments/${a.id}/download" target="_blank">${escapeHtml(a.filename)}</a>
              <span class="subtle">${(a.size_bytes / 1024).toFixed(1)} KB</span>
              <button class="btn btn-ghost btn-danger" onclick="deleteAttachment(${issue.id}, ${a.id})">Delete</button>
            </div>
          `).join("")}
        </div>

        <div class="card" style="margin-bottom:16px">
          <h2>QA Checklist</h2>
          ${state.checklist.length === 0 ? `<div class="subtle">No checklist items yet.</div>` : ""}
          ${state.checklist.map(c => `
            <div class="checklist-row ${c.is_done ? "done" : ""}">
              <input type="checkbox" ${c.is_done ? "checked" : ""} onchange="toggleChecklistItem(${issue.id}, ${c.id})">
              <span class="check-text">${escapeHtml(c.text)}</span>
              <button class="btn btn-ghost btn-danger" style="margin-left:auto;padding:2px 8px" onclick="deleteChecklistItem(${issue.id}, ${c.id})">x</button>
            </div>
          `).join("")}
          <div class="checklist-add-row">
            <input type="text" id="cl-new-item" placeholder="Add a checklist item..." onkeydown="if(event.key==='Enter') addChecklistItem(${issue.id})">
            <button class="btn btn-ghost" onclick="addChecklistItem(${issue.id})">Add</button>
          </div>
        </div>


        <div class="card" style="margin-bottom:16px">
          <div class="flex-between">
            <h2>Timesheet</h2>
            <div class="timelog-total">${(state.timeLogs || []).reduce((sum, t) => sum + t.hours, 0).toFixed(1)}h</div>
          </div>
          <div class="stopwatch-row">
            <div class="stopwatch-display" id="stopwatch-display">00:00:00</div>
            <button class="btn btn-primary" id="stopwatch-btn" onclick="toggleStopwatch(${issue.id})">Start</button>
          </div>
          ${(state.timeLogs || []).length === 0 ? `<div class="subtle">No time logged yet.</div>` : ""}
          ${(state.timeLogs || []).map(t => `
            <div class="timelog-row">
              <div>
                <b>${t.hours}h</b> by ${escapeHtml(t.user?.username || "")} - ${escapeHtml(t.note || "")}
                <div class="subtle">${fmtDate(t.logged_at)}</div>
              </div>
              <button class="btn btn-ghost btn-danger" onclick="deleteTimeLog(${issue.id}, ${t.id})">Delete</button>
            </div>
          `).join("")}
          <div class="timelog-form">
            <div class="field" style="margin-bottom:0">
              <label>Hours</label>
              <input type="number" step="0.25" min="0" id="tl-hours">
            </div>
            <div class="field" style="margin-bottom:0;flex:1">
              <label>Note</label>
              <input type="text" id="tl-note" placeholder="What did you work on?">
            </div>
            <button class="btn btn-primary" onclick="addTimeLog(${issue.id})">Log time</button>
          </div>
        </div>


        <div class="card">
          <div class="flex-between">
            <h2>Comments</h2>
            <div class="gap-8">
              <button class="btn btn-ai" ${state.loading ? "disabled" : ""} onclick="askAiSuggest(${issue.id})">
                ${state.loading ? '<span class="spin"></span>' : ""} Ask AI for root cause
              </button>
              <button class="btn btn-ai" ${state.loading ? "disabled" : ""} onclick="askAiCodeFix(${issue.id})">
                ${state.loading ? '<span class="spin"></span>' : ""} Suggest code fix
              </button>
            </div>
          </div>
          ${state.comments.map(c => `
            <div class="comment ${c.is_ai ? "ai" : ""}">
              <div class="comment-head">${c.is_ai ? "AI suggestion" : escapeHtml(c.user?.username || "user")} - ${fmtDate(c.created_at)}</div>
              <div>${renderCommentBody(c.body)}</div>
            </div>
          `).join("")}
          <div class="field" style="margin-top:12px">
            <textarea id="new-comment" rows="3" placeholder="Add a comment..."></textarea>
          </div>
          <button class="btn btn-primary" onclick="postComment(${issue.id}, document.getElementById('new-comment').value); document.getElementById('new-comment').value=''">Post comment</button>
        </div>

        <div class="card" style="margin-top:16px">
          <h2>AI Stack Trace Analyzer</h2>
          <textarea class="stacktrace-input" id="stacktrace-input" placeholder="Paste server log or error stack trace here..."></textarea>
          <button class="btn btn-ai" style="margin-top:8px" ${state.stackTraceLoading ? "disabled" : ""} onclick="analyzeStackTrace(${issue.id})">
            ${state.stackTraceLoading ? '<span class="spin"></span>' : ""} Analyze Stack Trace
          </button>
          ${state.stackTraceResult ? `
            <div class="stacktrace-result">
              <b>Probable cause:</b> ${escapeHtml(state.stackTraceResult.probable_cause || state.stackTraceResult.error || "")}<br>
              ${state.stackTraceResult.recommendation ? `<b>Recommendation:</b> ${escapeHtml(state.stackTraceResult.recommendation)}` : ""}
            </div>
          ` : ""}
        </div>
      </div>

      <div>
        <div class="card">
          <h2>Details</h2>
          <div class="meta-row"><label>Status</label>
            <select onchange="updateIssueField(${issue.id}, 'status', this.value)">
              ${["open","in_progress","resolved","closed"].map(s => `<option value="${s}" ${issue.status===s?"selected":""}>${s}</option>`).join("")}
            </select>
          </div>
          <div class="meta-row"><label>Priority</label>
            <select onchange="updateIssueField(${issue.id}, 'priority', this.value)">
              ${["low","medium","high","critical"].map(p => `<option value="${p}" ${issue.priority===p?"selected":""}>${p}</option>`).join("")}
            </select>
          </div>
          <div class="meta-row"><label>Type</label>
            <select onchange="updateIssueField(${issue.id}, 'issue_type', this.value)">
              ${["bug","feature","task","question"].map(t => `<option value="${t}" ${issue.issue_type===t?"selected":""}>${t}</option>`).join("")}
            </select>
          </div>
          <div class="meta-row"><label>Assignee</label>
            <select onchange="updateIssueField(${issue.id}, 'assignee_id', this.value ? Number(this.value) : null)">
              <option value="">Unassigned</option>
              ${state.users.map(u => `<option value="${u.id}" ${issue.assignee && issue.assignee.id===u.id ? "selected":""}>${escapeHtml(u.username)}</option>`).join("")}
            </select>
          </div>
          <div class="meta-row"><label>Milestone</label>
            <select onchange="updateIssueField(${issue.id}, 'milestone_id', this.value ? Number(this.value) : null)">
              <option value="">None</option>
              ${state.milestones.map(m => `<option value="${m.id}" ${issue.milestone_id===m.id?"selected":""}>${escapeHtml(m.title)}</option>`).join("")}
            </select>
          </div>
          <div class="meta-row"><label>Sprint</label>
            <select onchange="updateIssueField(${issue.id}, 'sprint_id', this.value ? Number(this.value) : null)">
              <option value="">None</option>
              ${state.sprints.map(sp => `<option value="${sp.id}" ${issue.sprint_id===sp.id?"selected":""}>${escapeHtml(sp.name)}</option>`).join("")}
            </select>
          </div>
          <div class="meta-row"><label>Reporter</label><span>${escapeHtml(issue.reporter?.username || "")}</span></div>
          <div class="meta-row"><label>Due date</label><input type="date" style="width:auto;${isOverdue(issue) ? 'border-color:var(--danger);color:var(--danger);' : ''}" value="${issue.due_date ? issue.due_date.substring(0,10) : ''}" onchange="updateIssueField(${issue.id}, 'due_date', this.value || null)"></div>
          <div class="meta-row"><label>Created</label><span>${fmtDate(issue.created_at)}</span></div>
        </div>
        <button class="btn btn-ai" style="width:100%;margin-top:12px" ${state.loading ? "disabled" : ""} onclick="checkDuplicates(${issue.id})">
          ${state.loading ? '<span class="spin"></span>' : ""} Check for duplicates
        </button>
        <button class="btn btn-ai" style="width:100%;margin-top:8px" onclick="suggestAssigneeForIssue(${issue.id})">
          ${state.assigneeSuggestion === "loading" ? '<span class="spin"></span>' : ""} Suggest assignee
        </button>
        ${state.assigneeSuggestion && state.assigneeSuggestion !== "loading" ? (
          state.assigneeSuggestion.error
            ? `<div class="assignee-suggestion">Error: ${escapeHtml(state.assigneeSuggestion.error)}</div>`
            : `<div class="assignee-suggestion"><b>${escapeHtml(state.assigneeSuggestion.username)}</b> - ${escapeHtml(state.assigneeSuggestion.reason)}<br><button class="btn btn-ghost" style="margin-top:6px" onclick="updateIssueField(${issue.id}, 'assignee_id', ${state.assigneeSuggestion.user_id})">Assign</button></div>`
        ) : ""}
        <button class="btn btn-ai" style="width:100%;margin-top:8px" ${state.assigneeComparisonLoading ? "disabled" : ""} onclick="compareAssignees(${issue.id})">
          ${state.assigneeComparisonLoading ? '<span class="spin"></span>' : ""} Compare all candidates
        </button>
        ${state.assigneeComparison ? `
          <table class="compare-table">
            <thead><tr><th>User</th><th>Score</th><th>Reason</th></tr></thead>
            <tbody>
              ${state.assigneeComparison.map(c => c.error ? `<tr><td colspan="3">Error: ${escapeHtml(c.error)}</td></tr>` : `
                <tr>
                  <td>${escapeHtml(c.username)}</td>
                  <td><span class="score-bar-track"><span class="score-bar-fill" style="width:${c.score}%"></span></span>${c.score}</td>
                  <td>${escapeHtml(c.reason)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        ` : ""}
        <button class="btn btn-ai" style="width:100%;margin-top:8px" ${state.issueMetricsLoading ? "disabled" : ""} onclick="estimateIssueMetrics(${issue.id})">
          ${state.issueMetricsLoading ? '<span class="spin"></span>' : ""} Estimate metrics
        </button>
        ${state.issueMetrics ? (
          state.issueMetrics.error
            ? `<div class="assignee-suggestion">Error: ${escapeHtml(state.issueMetrics.error)}</div>`
            : `<div class="metrics-row">
                <div class="metric-box"><div class="metric-num">${state.issueMetrics.frustration_score}</div><div class="metric-label">Frustration score</div></div>
                <div class="metric-box"><div class="metric-num">${state.issueMetrics.predicted_fix_hours}h</div><div class="metric-label">Predicted fix time</div></div>
              </div>`
        ) : ""}
      </div>
    </div>
  `;
}

function milestonesHtml() {
  return `
    <div class="topbar">
      <h1>Milestones</h1>
      <button class="btn btn-primary" onclick="state.modal='newMilestone'; render()">+ New milestone</button>
    </div>
    ${state.milestones.length === 0 ? `<div class="empty-state">No milestones yet for this project.</div>` : ""}
    <div class="card-grid">${state.milestones.map(milestoneCardHtml).join("")}</div>
  `;
}

function milestoneCardHtml(m) {
  const pct = m.issue_count ? Math.round((m.done_count / m.issue_count) * 100) : 0;
  return `
    <div class="card milestone-card">
      <div class="flex-between">
        <b>${escapeHtml(m.title)}</b>
        <span class="badge ${m.status === "completed" ? "badge-resolved" : "badge-open"}">${m.status}</span>
      </div>
      <p class="subtle">${escapeHtml(m.description) || "No description"}</p>
      ${m.due_date ? `<div class="subtle">Due ${fmtDate(m.due_date)}</div>` : ""}
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="subtle">${m.done_count}/${m.issue_count} issues resolved</div>
      <div class="gap-8" style="margin-top:10px">
        <button class="btn btn-ghost" onclick="viewMilestoneIssues(${m.id})">View issues</button>
        <select onchange="updateMilestoneStatus(${m.id}, this.value)">
          <option value="open" ${m.status==="open"?"selected":""}>open</option>
          <option value="completed" ${m.status==="completed"?"selected":""}>completed</option>
        </select>
        <button class="btn btn-ghost btn-danger" onclick="deleteMilestone(${m.id}, '${escapeHtml(m.title)}')">Delete</button>
      </div>
    </div>
  `;
}

async function createMilestone(payload) {
  try {
    await apiFetch("/api/milestones", { method: "POST", body: JSON.stringify(payload) });
    state.modal = null;
    await loadMilestones();
    render();
  } catch (e) { alert(e.message); }
}
async function updateMilestoneStatus(id, status) {
  try {
    await apiFetch("/api/milestones/" + id, { method: "PATCH", body: JSON.stringify({ status }) });
    await loadMilestones();
    render();
  } catch (e) { alert(e.message); }
}
async function deleteMilestone(id, title) {
  if (!confirm(`Delete milestone "${title}"? Issues will be unassigned from it.`)) return;
  try {
    await apiFetch("/api/milestones/" + id, { method: "DELETE" });
    await loadMilestones();
    render();
  } catch (e) { alert(e.message); }
}
async function viewMilestoneIssues(id) {
  state.filters.milestone_id = id;
  state.filters.sprint_id = "";
  state.view = "issues";
  await loadIssues();
  render();
}

function sprintsHtml() {
  return `
    <div class="topbar">
      <h1>Sprints</h1>
      <button class="btn btn-primary" onclick="state.modal='newSprint'; render()">+ New sprint</button>
    </div>
    ${state.sprints.length === 0 ? `<div class="empty-state">No sprints yet for this project.</div>` : ""}
    <div class="card-grid">${state.sprints.map(sprintCardHtml).join("")}</div>
  `;
}

function sprintCardHtml(s) {
  const pct = s.issue_count ? Math.round((s.done_count / s.issue_count) * 100) : 0;
  const badge = s.status === "active" ? "badge-in_progress" : s.status === "completed" ? "badge-resolved" : "badge-open";
  return `
    <div class="card milestone-card">
      <div class="flex-between">
        <b>${escapeHtml(s.name)}</b>
        <span class="badge ${badge}">${s.status}</span>
      </div>
      <p class="subtle">${escapeHtml(s.goal) || "No goal set"}</p>
      ${s.start_date || s.end_date ? `<div class="subtle">${s.start_date ? fmtDate(s.start_date) : "?"} &rarr; ${s.end_date ? fmtDate(s.end_date) : "?"}</div>` : ""}
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="subtle">${s.done_count}/${s.issue_count} issues resolved</div>
      <div class="gap-8" style="margin-top:10px">
        <button class="btn btn-ghost" onclick="viewSprintIssues(${s.id})">View issues</button>
        <select onchange="updateSprintStatus(${s.id}, this.value)">
          <option value="planned" ${s.status==="planned"?"selected":""}>planned</option>
          <option value="active" ${s.status==="active"?"selected":""}>active</option>
          <option value="completed" ${s.status==="completed"?"selected":""}>completed</option>
        </select>
        <button class="btn btn-ghost btn-danger" onclick="deleteSprint(${s.id}, '${escapeHtml(s.name)}')">Delete</button>
      </div>
      <button class="btn btn-ai" style="width:100%;margin-top:10px" onclick="checkSprintRisk(${s.id})">
        ${state.sprintRisk[s.id] === "loading" ? '<span class="spin"></span>' : ""} Risk analysis
      </button>
      ${sprintRiskPanelHtml(s.id)}
      <button class="btn btn-ghost" style="width:100%;margin-top:8px" onclick="toggleCopilot(${s.id})">
        ${state.copilotOpen[s.id] ? "Hide" : "Chat with"} Sprint Copilot
      </button>
      ${copilotPanelHtml(s.id)}
      <button class="btn btn-ai" style="width:100%;margin-top:8px" onclick="planSprintWithAi(${s.id})">
        ${state.sprintPlanLoading === s.id ? '<span class="spin"></span>' : ""} Plan sprint with AI
      </button>
      ${sprintPlanPanelHtml(s.id)}
    </div>
  `;
}

function sprintRiskPanelHtml(sprintId) {
  const r = state.sprintRisk[sprintId];
  if (!r || r === "loading") return "";
  if (r.error) return `<div class="risk-panel risk-high">Error: ${escapeHtml(r.error)}</div>`;
  const level = r.risk_percent >= 60 ? "high" : r.risk_percent >= 30 ? "medium" : "low";
  return `
    <div class="risk-panel risk-${level}">
      <div class="risk-percent">${r.risk_percent}% risk of missing deadline</div>
      <div>${escapeHtml(r.reasoning || "")}</div>
      <div class="subtle" style="margin-top:4px"><b>Suggestion:</b> ${escapeHtml(r.recommendation || "")}</div>
    </div>
  `;
}

async function createSprint(payload) {
  try {
    await apiFetch("/api/sprints", { method: "POST", body: JSON.stringify(payload) });
    state.modal = null;
    await loadSprints();
    render();
  } catch (e) { alert(e.message); }
}
async function updateSprintStatus(id, status) {
  try {
    await apiFetch("/api/sprints/" + id, { method: "PATCH", body: JSON.stringify({ status }) });
    await loadSprints();
    render();
  } catch (e) { alert(e.message); }
}
async function deleteSprint(id, name) {
  if (!confirm(`Delete sprint "${name}"? Issues will be unassigned from it.`)) return;
  try {
    await apiFetch("/api/sprints/" + id, { method: "DELETE" });
    await loadSprints();
    render();
  } catch (e) { alert(e.message); }
}
async function viewSprintIssues(id) {
  state.filters.sprint_id = id;
  state.filters.milestone_id = "";
  state.view = "issues";
  await loadIssues();
  render();
}

function projectsHtml() {
  return `
    <div class="topbar">
      <h1>Projects</h1>
      <button class="btn btn-primary" onclick="state.modal='newProject'; render()">+ New project</button>
    </div>
    ${state.projects.map(p => `
      <div class="card" style="margin-bottom:10px">
        <div class="flex-between">
          <div>
            <div class="issue-key">${escapeHtml(p.key)}</div>
            <b>${escapeHtml(p.name)}</b>
            <div class="subtle">${escapeHtml(p.description)}</div>
          </div>
          <button class="btn btn-ghost" onclick="setProject(${p.id}); setView('issues')">View issues</button>
        </div>
      </div>
    `).join("")}
  `;
}

function adminHtml() {
  const s = state.adminStats || {};
  return `
    <div class="topbar">
      <h1>Admin</h1>
    </div>

    <div class="stat-row">
      <div class="card stat-card"><div class="stat-num">${s.total_users ?? 0}</div><div class="stat-label">Users</div></div>
      <div class="card stat-card"><div class="stat-num">${s.total_projects ?? 0}</div><div class="stat-label">Projects</div></div>
      <div class="card stat-card"><div class="stat-num">${s.total_issues ?? 0}</div><div class="stat-label">Issues</div></div>
      <div class="card stat-card"><div class="stat-num">${s.ai_triaged_issues ?? 0}</div><div class="stat-label">AI triaged</div></div>
    </div>

    <div class="card" style="margin-bottom:20px">
      <h2>Users</h2>
      <table class="admin-table">
        <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Joined</th><th></th></tr></thead>
        <tbody>
          ${state.adminUsers.map(u => `
            <tr>
              <td>${escapeHtml(u.username)}</td>
              <td>${escapeHtml(u.email)}</td>
              <td>
                <select onchange="changeUserRole(${u.id}, this.value)" ${u.id === state.user.id ? "disabled" : ""}>
                  <option value="member" ${u.role === "member" ? "selected" : ""}>member</option>
                  <option value="admin" ${u.role === "admin" ? "selected" : ""}>admin</option>
                </select>
              </td>
              <td class="subtle">${u.created_at ? fmtDate(u.created_at) : ""}</td>
              <td>
                ${u.id === state.user.id
                  ? `<span class="subtle">You</span>`
                  : `<button class="btn btn-ghost btn-danger" onclick="deleteUserAdmin(${u.id}, '${escapeHtml(u.username)}')">Delete</button>`}
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-bottom:20px">
      <h2>All projects</h2>
      <table class="admin-table">
        <thead><tr><th>Key</th><th>Name</th><th>Created</th><th></th></tr></thead>
        <tbody>
          ${state.adminProjects.map(p => `
            <tr>
              <td class="issue-key">${escapeHtml(p.key)}</td>
              <td>${escapeHtml(p.name)}</td>
              <td class="subtle">${fmtDate(p.created_at)}</td>
              <td><button class="btn btn-ghost btn-danger" onclick="deleteProjectAdmin(${p.id}, '${escapeHtml(p.name)}')">Delete</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>All issues</h2>
      <table class="admin-table">
        <thead><tr><th>Title</th><th>Status</th><th>Priority</th><th>Created</th><th></th></tr></thead>
        <tbody>
          ${state.adminIssues.map(i => `
            <tr>
              <td>${escapeHtml(i.title)}</td>
              <td><span class="badge ${badgeClass(i.status)}">${i.status}</span></td>
              <td>${i.priority}</td>
              <td class="subtle">${fmtDate(i.created_at)}</td>
              <td><button class="btn btn-ghost btn-danger" onclick="deleteIssueAdmin(${i.id}, '${escapeHtml(i.title)}')">Delete</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function modalHtml() {
  if (state.modal === "editProfile") {
    const mine = state.profiles.find(p => p.user_id === state.user.id) || {};
    return `
      <div class="modal-overlay" onclick="if(event.target===this){state.modal=null; render()}">
        <div class="modal">
          <h2>Edit your profile</h2>
          <div class="field"><label>Specialization</label><input type="text" id="ep-spec" value="${escapeHtml(mine.specialization || "")}"></div>
          <div class="field"><label>Skills (comma-separated)</label><input type="text" id="ep-skills" value="${escapeHtml((mine.skills || []).join(", "))}"></div>
          <div class="field"><label>Years of experience</label><input type="number" id="ep-exp" value="${mine.experience_years || 0}"></div>
          <div class="field"><label>Bio</label><textarea id="ep-bio" rows="3">${escapeHtml(mine.bio || "")}</textarea></div>
          <div class="gap-8">
            <button class="btn btn-primary" onclick="saveMyProfile(document.getElementById('ep-skills').value, document.getElementById('ep-spec').value, document.getElementById('ep-exp').value, document.getElementById('ep-bio').value)">Save</button>
            <button class="btn btn-ghost" onclick="state.modal=null; render()">Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal === "newSlaPolicy") {
    return `
      <div class="modal-overlay" onclick="if(event.target===this){state.modal=null; render()}">
        <div class="modal">
          <h2>New SLA policy</h2>
          <div class="field"><label>Name</label><input type="text" id="sla-name" placeholder="e.g. Critical Response"></div>
          <div class="field"><label>Priority</label>
            <select id="sla-priority">
              <option value="critical">critical</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </div>
          <div class="field"><label>Resolution time (hours)</label><input type="number" id="sla-hours" value="24"></div>
          <div class="field"><label>Escalate to role</label>
            <select id="sla-role">
              <option value="admin">admin</option>
              <option value="member">member</option>
            </select>
          </div>
          <div class="gap-8">
            <button class="btn btn-primary" onclick="createSlaPolicy({
              project_id: state.currentProjectId,
              name: document.getElementById('sla-name').value,
              priority: document.getElementById('sla-priority').value,
              resolution_hours: Number(document.getElementById('sla-hours').value),
              escalate_to_role: document.getElementById('sla-role').value
            })">Create</button>
            <button class="btn btn-ghost" onclick="state.modal=null; render()">Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal === "newProject") {
    return `
      <div class="modal-overlay" onclick="if(event.target===this){state.modal=null; render()}">
        <div class="modal">
          <h2>New project</h2>
          <div class="field"><label>Key (short code, e.g. ENG)</label><input type="text" id="np-key"></div>
          <div class="field"><label>Name</label><input type="text" id="np-name"></div>
          <div class="field"><label>Description</label><textarea id="np-desc" rows="3"></textarea></div>
          <div class="gap-8">
            <button class="btn btn-primary" onclick="createProject(document.getElementById('np-key').value, document.getElementById('np-name').value, document.getElementById('np-desc').value)">Create</button>
            <button class="btn btn-ghost" onclick="state.modal=null; render()">Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal === "newIssue") {
    return `
      <div class="modal-overlay" onclick="if(event.target===this){state.modal=null; render()}">
        <div class="modal">
          <h2>New issue</h2>
          <div class="field">
            <label>Title</label>
            <input type="text" id="ni-title" oninput="clearTimeout(window._dupTimer); window._dupTimer = setTimeout(checkLiveDuplicates, 800)">
          </div>
          <div id="ni-dup-results"></div>
          <div class="field" style="margin-top:14px">
            <label>Description <button type="button" class="mic-btn" id="ni-mic-btn" onclick="toggleVoiceInput()" title="Voice input">&#127908;</button></label>
            <textarea id="ni-desc" rows="4" oninput="clearTimeout(window._dupTimer); window._dupTimer = setTimeout(checkLiveDuplicates, 800)"></textarea>
          </div>
          <div class="field">
            <label>GitHub PR link (optional)</label>
            <input type="text" id="ni-pr-link" placeholder="https://github.com/org/repo/pull/123">
          </div>
          <div class="field">
            <label>Milestone (optional)</label>
            <select id="ni-milestone">
              <option value="">None</option>
              ${state.milestones.map(m => `<option value="${m.id}">${escapeHtml(m.title)}</option>`).join("")}
            </select>
          </div>
          <div class="field">
            <label>Sprint (optional)</label>
            <select id="ni-sprint">
              <option value="">None</option>
              ${state.sprints.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join("")}
            </select>
          </div>
          <div class="field">
            <label><input type="checkbox" id="ni-ai" checked style="width:auto;display:inline"> Let AI triage priority, type, and tags</label>
          </div>
          <div class="gap-8">
            <button class="btn btn-primary" onclick="createIssue({
              project_id: state.currentProjectId,
              title: document.getElementById('ni-title').value,
              description: document.getElementById('ni-desc').value,
              pr_link: document.getElementById('ni-pr-link').value,
              milestone_id: document.getElementById('ni-milestone').value ? Number(document.getElementById('ni-milestone').value) : null,
              sprint_id: document.getElementById('ni-sprint').value ? Number(document.getElementById('ni-sprint').value) : null,
              use_ai_triage: document.getElementById('ni-ai').checked
            })">Create issue</button>
            <button class="btn btn-ghost" onclick="state.modal=null; render()">Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal === "newMilestone") {
    return `
      <div class="modal-overlay" onclick="if(event.target===this){state.modal=null; render()}">
        <div class="modal">
          <h2>New milestone</h2>
          <div class="field"><label>Title</label><input type="text" id="nm-title"></div>
          <div class="field"><label>Description</label><textarea id="nm-desc" rows="3"></textarea></div>
          <div class="field"><label>Due date</label><input type="date" id="nm-due"></div>
          <div class="gap-8">
            <button class="btn btn-primary" onclick="createMilestone({
              project_id: state.currentProjectId,
              title: document.getElementById('nm-title').value,
              description: document.getElementById('nm-desc').value,
              due_date: document.getElementById('nm-due').value || null
            })">Create</button>
            <button class="btn btn-ghost" onclick="state.modal=null; render()">Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal === "newSprint") {
    return `
      <div class="modal-overlay" onclick="if(event.target===this){state.modal=null; render()}">
        <div class="modal">
          <h2>New sprint</h2>
          <div class="field"><label>Name</label><input type="text" id="ns-name"></div>
          <div class="field"><label>Goal</label><textarea id="ns-goal" rows="3"></textarea></div>
          <div class="field"><label>Start date</label><input type="date" id="ns-start"></div>
          <div class="field"><label>End date</label><input type="date" id="ns-end"></div>
          <div class="gap-8">
            <button class="btn btn-primary" onclick="createSprint({
              project_id: state.currentProjectId,
              name: document.getElementById('ns-name').value,
              goal: document.getElementById('ns-goal').value,
              start_date: document.getElementById('ns-start').value || null,
              end_date: document.getElementById('ns-end').value || null
            })">Create</button>
            <button class="btn btn-ghost" onclick="state.modal=null; render()">Cancel</button>
          </div>
        </div>
      </div>
    `;
  }
  return "";
}

function render() {
  const app = document.getElementById("app");
  if (!state.token) {
    app.innerHTML = authViewHtml();
    return;
  }

  let body = "";
  if (state.view === "home") body = homeHtml();
  else if (state.view === "dashboard") body = dashboardHtml();
  else if (state.view === "issues") body = issuesHtml();
  else if (state.view === "issueDetail") body = issueDetailHtml();
  else if (state.view === "milestones") body = milestonesHtml();
  else if (state.view === "sprints") body = sprintsHtml();
  else if (state.view === "projects") body = projectsHtml();
  else if (state.view === "admin") body = adminHtml();
  else if (state.view === "workload") body = workloadHtml();
  else if (state.view === "reports") body = reportsHtml();
  else if (state.view === "profiles") body = profilesHtml();
  else if (state.view === "sla") body = slaHtml();
  else if (state.view === "about") body = aboutHtml();
  else if (state.view === "features") body = featuresHtml();
  else if (state.view === "chat") body = chatHtml();

  app.innerHTML = `
    <div class="shell">
      ${sidebarHtml()}
      <div class="main">${body}</div>
    </div>
    ${modalHtml()}
    ${floatingChatHtml()}
  `;
}

init();


function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
}

function toggleTheme() {
  applyTheme(state.theme === "dark" ? "light" : "dark");
  render();
}









async function loadWeeklyReport() {
  state.weeklyReport = "loading";
  render();
  try {
    const params = new URLSearchParams();
    if (state.currentProjectId) params.set("project_id", state.currentProjectId);
    state.weeklyReport = await apiFetch("/api/reports/weekly?" + params.toString(), { method: "POST" });
  } catch (e) {
    state.weeklyReport = { report: "Could not generate report: " + e.message, created_count: 0, resolved_count: 0, comments_count: 0, top_tags: [] };
  }
  render();
}

async function loadWorkload() {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("project_id", state.currentProjectId);
  state.workload = await apiFetch("/api/dashboard/workload?" + params.toString());
}

async function suggestAssigneeForIssue(id) {
  state.assigneeSuggestion = "loading";
  render();
  try {
    state.assigneeSuggestion = await apiFetch("/api/issues/" + id + "/suggest-assignee", { method: "POST" });
  } catch (e) {
    state.assigneeSuggestion = { error: e.message };
  }
  render();
}

function reportsHtml() {
  const r = state.weeklyReport;
  return `
    <div class="topbar">
      <h1>Weekly AI Report</h1>
      <button class="btn btn-ai" onclick="loadWeeklyReport()">${r ? "Regenerate" : "Generate report"}</button>
    </div>
    ${!r ? `<div class="empty-state">Click "Generate report" to summarize this project's last 7 days.</div>` : ""}
    ${r === "loading" ? `<div class="empty-state"><span class="spin"></span> Generating...</div>` : ""}
    ${r && r !== "loading" ? `
      <div class="stat-row">
        <div class="card stat-card"><div class="stat-num">${r.created_count}</div><div class="stat-label">Created</div></div>
        <div class="card stat-card"><div class="stat-num">${r.resolved_count}</div><div class="stat-label">Resolved</div></div>
        <div class="card stat-card"><div class="stat-num">${r.comments_count}</div><div class="stat-label">Comments</div></div>
        <div class="card stat-card"><div class="stat-num">${(r.top_tags||[]).length}</div><div class="stat-label">Top tags</div></div>
      </div>
      <div class="card report-card">${escapeHtml(r.report)}</div>
    ` : ""}

    <div class="topbar" style="margin-top:32px">
      <h1>Activity Summary</h1>
      <button class="btn btn-ai" onclick="loadActivitySummary()">${state.activitySummary ? "Refresh" : "Summarize recent activity"}</button>
    </div>
    ${!state.activitySummary ? `<div class="empty-state">Click "Summarize recent activity" to catch up on the last 2 weeks.</div>` : ""}
    ${state.activitySummary === "loading" ? `<div class="empty-state"><span class="spin"></span> Summarizing...</div>` : ""}
    ${state.activitySummary && state.activitySummary !== "loading" ? `
      <div class="card report-card">${escapeHtml(state.activitySummary.summary)}</div>
      <div class="subtle" style="margin-top:8px">${state.activitySummary.item_count} activity items considered</div>
    ` : ""}
  `;
}

function workloadHtml() {
  const max = Math.max(1, ...state.workload.map(w => w.open_count + w.in_progress_count));
  return `
    <div class="topbar"><h1>Team Workload</h1></div>
    <div class="card">
      ${state.workload.length === 0 ? `<div class="empty-state">No team members yet.</div>` : ""}
      ${state.workload.map(w => {
        const active = w.open_count + w.in_progress_count;
        const pct = Math.round((active / max) * 100);
        return `
          <div class="workload-row">
            <div style="width:120px">${escapeHtml(w.username)}</div>
            <div class="workload-bar-track"><div class="workload-bar-fill" style="width:${pct}%"></div></div>
            <div class="subtle" style="width:160px;text-align:right">${active} active / ${w.total_count} total</div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}









function isOverdue(issue) {
  if (!issue.due_date) return false;
  if (issue.status === "resolved" || issue.status === "closed") return false;
  return new Date(issue.due_date) < new Date();
}






async function exportIssuesCsv() {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("project_id", state.currentProjectId);
  if (state.filters.status) params.set("status", state.filters.status);
  if (state.filters.priority) params.set("priority", state.filters.priority);

  try {
    const res = await fetch("/api/issues/export/csv?" + params.toString(), {
      headers: { Authorization: "Bearer " + state.token },
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "issues_export.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert(e.message);
  }
}




async function checkSprintRisk(sprintId) {
  state.sprintRisk[sprintId] = "loading";
  render();
  try {
    state.sprintRisk[sprintId] = await apiFetch("/api/sprints/" + sprintId + "/risk", { method: "POST" });
  } catch (e) {
    state.sprintRisk[sprintId] = { error: e.message };
  }
  render();
}




async function loadActivitySummary() {
  state.activitySummary = "loading";
  render();
  try {
    const params = new URLSearchParams();
    if (state.currentProjectId) params.set("project_id", state.currentProjectId);
    state.activitySummary = await apiFetch("/api/reports/activity?" + params.toString(), { method: "POST" });
  } catch (e) {
    state.activitySummary = { summary: "Could not summarize: " + e.message, item_count: 0 };
  }
  render();
}




function toggleCopilot(sprintId) {
  state.copilotOpen[sprintId] = !state.copilotOpen[sprintId];
  if (!state.copilotChats[sprintId]) state.copilotChats[sprintId] = [];
  render();
}

function copilotPanelHtml(sprintId) {
  if (!state.copilotOpen[sprintId]) return "";
  const chat = state.copilotChats[sprintId] || [];
  const loading = state.copilotLoading[sprintId];
  return `
    <div class="copilot-panel">
      <div class="copilot-messages" id="copilot-msgs-${sprintId}">
        ${chat.length === 0 ? `<div class="subtle">Ask about blockers, priorities, or progress in this sprint.</div>` : ""}
        ${chat.map(m => `
          <div class="copilot-msg ${m.role}">
            <div class="bubble">${escapeHtml(m.text)}</div>
          </div>
        `).join("")}
        ${loading ? `<div class="copilot-msg assistant"><div class="bubble"><span class="spin"></span></div></div>` : ""}
      </div>
      <div class="copilot-input-row">
        <input type="text" id="copilot-input-${sprintId}" placeholder="Ask the copilot..."
          onkeydown="if(event.key==='Enter') sendCopilotMessage(${sprintId})">
        <button class="btn btn-primary" onclick="sendCopilotMessage(${sprintId})">Send</button>
      </div>
    </div>
  `;
}

async function sendCopilotMessage(sprintId) {
  const input = document.getElementById("copilot-input-" + sprintId);
  const question = input.value.trim();
  if (!question) return;
  input.value = "";

  if (!state.copilotChats[sprintId]) state.copilotChats[sprintId] = [];
  const history = state.copilotChats[sprintId];
  history.push({ role: "user", text: question });
  state.copilotLoading[sprintId] = true;
  render();

  try {
    const historyForApi = history.slice(0, -1).map(m => ({ role: m.role, text: m.text }));
    const res = await apiFetch("/api/sprints/" + sprintId + "/copilot", {
      method: "POST",
      body: JSON.stringify({ question, history: historyForApi }),
    });
    history.push({ role: "assistant", text: res.answer });
  } catch (e) {
    history.push({ role: "assistant", text: "Error: " + e.message });
  }
  state.copilotLoading[sprintId] = false;
  render();
}








async function addTimeLog(issueId) {
  const hoursEl = document.getElementById("tl-hours");
  const noteEl = document.getElementById("tl-note");
  const hours = parseFloat(hoursEl.value);
  if (!hours || hours <= 0) {
    alert("Enter a valid number of hours");
    return;
  }
  try {
    await apiFetch("/api/issues/" + issueId + "/timelogs", {
      method: "POST",
      body: JSON.stringify({ hours, note: noteEl.value }),
    });
    hoursEl.value = "";
    noteEl.value = "";
    state.timeLogs = await apiFetch("/api/issues/" + issueId + "/timelogs");
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteTimeLog(issueId, logId) {
  if (!confirm("Delete this time log entry?")) return;
  try {
    await apiFetch("/api/issues/timelogs/" + logId, { method: "DELETE" });
    state.timeLogs = await apiFetch("/api/issues/" + issueId + "/timelogs");
    render();
  } catch (e) {
    alert(e.message);
  }
}







let voiceRecognition = null;
let voiceListening = false;

function toggleVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Voice input is not supported in this browser. Try Chrome or Edge.");
    return;
  }

  const btn = document.getElementById("ni-mic-btn");
  const textarea = document.getElementById("ni-desc");

  if (voiceListening) {
    voiceRecognition.stop();
    return;
  }

  voiceRecognition = new SpeechRecognition();
  voiceRecognition.continuous = false;
  voiceRecognition.interimResults = false;
  voiceRecognition.lang = "en-US";

  voiceRecognition.onstart = () => {
    voiceListening = true;
    if (btn) btn.classList.add("recording");
  };

  voiceRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    if (textarea) {
      textarea.value = (textarea.value ? textarea.value + " " : "") + transcript;
    }
  };

  voiceRecognition.onerror = (event) => {
    if (event.error !== "aborted") {
      alert("Voice input error: " + event.error);
    }
  };

  voiceRecognition.onend = () => {
    voiceListening = false;
    if (btn) btn.classList.remove("recording");
  };

  voiceRecognition.start();
}







async function addChecklistItem(issueId) {
  const input = document.getElementById("cl-new-item");
  const text = input.value.trim();
  if (!text) return;
  try {
    await apiFetch("/api/issues/" + issueId + "/checklist", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    input.value = "";
    state.checklist = await apiFetch("/api/issues/" + issueId + "/checklist");
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function toggleChecklistItem(issueId, itemId) {
  try {
    await apiFetch("/api/issues/checklist/" + itemId + "/toggle", { method: "PATCH" });
    state.checklist = await apiFetch("/api/issues/" + issueId + "/checklist");
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteChecklistItem(issueId, itemId) {
  try {
    await apiFetch("/api/issues/checklist/" + itemId, { method: "DELETE" });
    state.checklist = await apiFetch("/api/issues/" + issueId + "/checklist");
    render();
  } catch (e) {
    alert(e.message);
  }
}



function notifDropdownHtml() {
  return `
    <div class="notif-dropdown" onclick="event.stopPropagation()">
      ${state.notifications.length === 0 ? `<div class="notif-item">No notifications yet.</div>` : ""}
      ${state.notifications.map(n => `
        <div class="notif-item ${n.is_read ? "" : "unread"}" onclick="openNotification(${n.id}, ${n.issue_id || "null"})">
          ${escapeHtml(n.message)}
          <div class="subtle">${fmtDate(n.created_at)}</div>
        </div>
      `).join("")}
    </div>
  `;
}

async function toggleNotifDropdown(event) {
  event.stopPropagation();
  state.notifDropdownOpen = !state.notifDropdownOpen;
  if (state.notifDropdownOpen) {
    state.notifications = await apiFetch("/api/notifications");
  }
  render();
}

async function openNotification(notifId, issueId) {
  try {
    await apiFetch("/api/notifications/" + notifId + "/read", { method: "PATCH" });
  } catch (e) {}
  state.notifDropdownOpen = false;
  if (issueId) {
    await openIssue(issueId);
  } else {
    render();
  }
}

async function loadUnreadNotifCount() {
  try {
    state.notifications = await apiFetch("/api/notifications");
  } catch (e) {}
}





async function analyzeStackTrace(issueId) {
  const input = document.getElementById("stacktrace-input");
  const trace = input.value.trim();
  if (!trace) {
    alert("Paste a stack trace or error log first");
    return;
  }
  state.stackTraceLoading = true;
  state.stackTraceResult = null;
  render();
  try {
    state.stackTraceResult = await apiFetch("/api/issues/" + issueId + "/analyze-stack-trace", {
      method: "POST",
      body: JSON.stringify({ stack_trace: trace }),
    });
  } catch (e) {
    state.stackTraceResult = { error: e.message };
  }
  state.stackTraceLoading = false;
  render();
}





function sprintPlanPanelHtml(sprintId) {
  const plan = state.sprintPlans[sprintId];
  if (!plan) return "";
  if (plan.error) return `<div class="plan-result">Error: ${escapeHtml(plan.error)}</div>`;
  return `
    <div class="plan-result">
      <div>${escapeHtml(plan.reasoning || "")}</div>
      <div class="plan-issue-list">
        ${(plan.selected_issue_ids || []).length === 0 ? `<div class="subtle">No issues selected.</div>` : ""}
        ${(plan.selected_issue_ids || []).map(id => `<div class="plan-issue-row">- Issue #${id}</div>`).join("")}
      </div>
      ${(plan.selected_issue_ids || []).length > 0 ? `
        <button class="btn btn-primary" onclick="applySprintPlan(${sprintId})">Apply plan (add to sprint)</button>
      ` : ""}
    </div>
  `;
}

async function planSprintWithAi(sprintId) {
  state.sprintPlanLoading = sprintId;
  state.sprintPlans[sprintId] = null;
  render();
  try {
    state.sprintPlans[sprintId] = await apiFetch("/api/sprints/" + sprintId + "/plan", { method: "POST" });
  } catch (e) {
    state.sprintPlans[sprintId] = { error: e.message };
  }
  state.sprintPlanLoading = null;
  render();
}

async function applySprintPlan(sprintId) {
  const plan = state.sprintPlans[sprintId];
  if (!plan || !plan.selected_issue_ids) return;
  try {
    await apiFetch("/api/sprints/" + sprintId + "/plan/apply", {
      method: "POST",
      body: JSON.stringify({ issue_ids: plan.selected_issue_ids }),
    });
    state.sprintPlans[sprintId] = null;
    await loadSprints();
    render();
  } catch (e) {
    alert(e.message);
  }
}



let stopwatchInterval = null;
let stopwatchStartTime = null;
let stopwatchRunning = false;

function toggleStopwatch(issueId) {
  const btn = document.getElementById("stopwatch-btn");
  const display = document.getElementById("stopwatch-display");

  if (!stopwatchRunning) {
    stopwatchStartTime = Date.now();
    stopwatchRunning = true;
    if (btn) btn.textContent = "Stop & Log";
    stopwatchInterval = setInterval(() => {
      const elapsed = Date.now() - stopwatchStartTime;
      const h = String(Math.floor(elapsed / 3600000)).padStart(2, "0");
      const m = String(Math.floor((elapsed % 3600000) / 60000)).padStart(2, "0");
      const s = String(Math.floor((elapsed % 60000) / 1000)).padStart(2, "0");
      const el = document.getElementById("stopwatch-display");
      if (el) el.textContent = `${h}:${m}:${s}`;
    }, 1000);
  } else {
    clearInterval(stopwatchInterval);
    stopwatchRunning = false;
    const elapsedMs = Date.now() - stopwatchStartTime;
    const hours = Math.round((elapsedMs / 3600000) * 100) / 100;
    if (btn) btn.textContent = "Start";
    if (display) display.textContent = "00:00:00";

    if (hours < 0.01) {
      return;
    }
    apiFetch("/api/issues/" + issueId + "/timelogs", {
      method: "POST",
      body: JSON.stringify({ hours, note: "Logged via stopwatch" }),
    }).then(async () => {
      state.timeLogs = await apiFetch("/api/issues/" + issueId + "/timelogs");
      render();
    }).catch(e => alert(e.message));
  }
}






async function uploadFile(issueId, file) {
  const formData = new FormData();
  formData.append("file", file);
  try {
    await fetch("/api/issues/" + issueId + "/attachments", {
      method: "POST",
      headers: { Authorization: "Bearer " + state.token },
      body: formData,
    });
    state.attachments = await apiFetch("/api/issues/" + issueId + "/attachments");
    render();
  } catch (e) {
    alert("Upload failed: " + e.message);
  }
}

function handleFileDrop(event, issueId) {
  event.preventDefault();
  document.getElementById("dropzone").classList.remove("dragover");
  const file = event.dataTransfer.files[0];
  if (file) uploadFile(issueId, file);
}

function handleFileSelect(event, issueId) {
  const file = event.target.files[0];
  if (file) uploadFile(issueId, file);
  event.target.value = "";
}

async function deleteAttachment(issueId, attachmentId) {
  if (!confirm("Delete this attachment?")) return;
  try {
    await apiFetch("/api/issues/attachments/" + attachmentId, { method: "DELETE" });
    state.attachments = await apiFetch("/api/issues/" + issueId + "/attachments");
    render();
  } catch (e) {
    alert(e.message);
  }
}






function profilesHtml() {
  return `
    <div class="topbar"><h1>Team Profiles</h1></div>
    <div class="card-grid">
      ${state.profiles.map(p => `
        <div class="card profile-card">
          <div class="flex-between">
            <b>${escapeHtml(p.username)}</b>
            ${p.user_id === state.user.id ? `<button class="btn btn-ghost" onclick="state.modal='editProfile'; render()">Edit</button>` : ""}
          </div>
          <div class="subtle">${escapeHtml(p.specialization) || "No specialization set"} - ${p.experience_years} yrs experience</div>
          <p class="subtle">${escapeHtml(p.bio) || ""}</p>
          <div class="profile-skills">
            ${(p.skills || []).length === 0 ? `<span class="subtle">No skills listed</span>` : ""}
            ${(p.skills || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("")}
          </div>
          <div class="subtle" style="margin-top:8px">${p.active_issue_count} active - ${p.resolved_issue_count} resolved</div>
        </div>
      `).join("")}
    </div>
  `;
}

async function saveMyProfile(skillsStr, specialization, experienceYears, bio) {
  try {
    await apiFetch("/api/profiles/me", {
      method: "PATCH",
      body: JSON.stringify({
        skills: skillsStr.split(",").map(s => s.trim()).filter(Boolean),
        specialization,
        experience_years: Number(experienceYears) || 0,
        bio,
      }),
    });
    state.modal = null;
    state.profiles = await apiFetch("/api/profiles");
    render();
  } catch (e) {
    alert(e.message);
  }
}

function slaHtml() {
  return `
    <div class="topbar">
      <h1>SLA Management</h1>
      <button class="btn btn-primary" onclick="state.modal='newSlaPolicy'; render()">+ New policy</button>
    </div>
    <div class="card" style="margin-bottom:20px">
      <h2>Active Breaches</h2>
      ${state.slaBreaches.length === 0 ? `<div class="subtle">No SLA breaches right now.</div>` : ""}
      ${state.slaBreaches.map(b => `
        <div class="sla-breach-row">
          <div><b>#${b.number} ${escapeHtml(b.title)}</b> - ${b.priority} priority, ${b.policy_name}</div>
          <div>${b.hours_overdue}h overdue -> escalate to ${escapeHtml(b.escalate_to_role)}</div>
        </div>
      `).join("")}
    </div>
    <div class="card">
      <h2>SLA Policies</h2>
      ${state.slaPolicies.length === 0 ? `<div class="subtle">No policies set for this project.</div>` : ""}
      <table class="admin-table">
        <thead><tr><th>Name</th><th>Priority</th><th>Resolution time</th><th>Escalate to</th><th></th></tr></thead>
        <tbody>
          ${state.slaPolicies.map(p => `
            <tr>
              <td>${escapeHtml(p.name)}</td>
              <td>${p.priority}</td>
              <td>${p.resolution_hours}h</td>
              <td>${escapeHtml(p.escalate_to_role)}</td>
              <td><button class="btn btn-ghost btn-danger" onclick="deleteSlaPolicy(${p.id})">Delete</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function createSlaPolicy(payload) {
  try {
    await apiFetch("/api/sla/policies", { method: "POST", body: JSON.stringify(payload) });
    state.modal = null;
    await setView("sla");
  } catch (e) {
    alert(e.message);
  }
}

async function deleteSlaPolicy(id) {
  if (!confirm("Delete this SLA policy?")) return;
  try {
    await apiFetch("/api/sla/policies/" + id, { method: "DELETE" });
    await setView("sla");
  } catch (e) {
    alert(e.message);
  }
}

async function compareAssignees(issueId) {
  state.assigneeComparisonLoading = true;
  state.assigneeComparison = null;
  render();
  try {
    state.assigneeComparison = await apiFetch("/api/issues/" + issueId + "/compare-assignees", { method: "POST" });
  } catch (e) {
    state.assigneeComparison = [{ error: e.message }];
  }
  state.assigneeComparisonLoading = false;
  render();
}

async function estimateIssueMetrics(issueId) {
  state.issueMetricsLoading = true;
  state.issueMetrics = null;
  render();
  try {
    state.issueMetrics = await apiFetch("/api/issues/" + issueId + "/estimate-metrics", { method: "POST" });
  } catch (e) {
    state.issueMetrics = { error: e.message };
  }
  state.issueMetricsLoading = false;
  render();
}









function aboutHtml() {
  return `
    <h1 style="margin-bottom:16px">About Triagey</h1>
    <div class="about-lead">Triagey exists so a small team can see, in one place, what's broken, what's next, and who's on it &mdash; with AI doing the first pass so people spend less time triaging and more time fixing.</div>
    <div class="about-body">
      <p>Every issue that comes in gets a home: a priority, a status, an owner. Triagey watches that flow and steps in where it helps &mdash; drafting a likely root cause, flagging a probable duplicate before it's filed twice, or suggesting who on the team is best placed to pick it up.</p>
      <p>Nothing here replaces judgment. AI suggestions are marked clearly wherever they appear, and every one is a starting point for a person to confirm, edit, or discard.</p>
    </div>
    <div class="card" style="max-width:640px">
      <h2>How an issue moves through Triagey</h2>
      <div class="lifecycle-row">
        <span class="badge badge-open">open</span><span class="lifecycle-arrow">&rarr;</span>
        <span class="badge badge-in_progress">in progress</span><span class="lifecycle-arrow">&rarr;</span>
        <span class="badge badge-resolved">resolved</span><span class="lifecycle-arrow">&rarr;</span>
        <span class="badge badge-closed">closed</span>
      </div>
      <p class="subtle" style="margin-top:12px">Reported, triaged &mdash; often with an AI-suggested priority and owner &mdash; worked, then closed out once verified.</p>
    </div>
  `;
}

function featuresHtml() {
  const groups = [
    { label: "AI assistance", tag: "ai", items: [
      ["Root cause suggestions", "Ask AI for a likely cause and a first-pass fix on any issue."],
      ["Duplicate detection", "Catches repeat reports as they're typed, or on demand."],
      ["Assignee suggestions", "Weighs current workload and skills to recommend an owner."],
      ["Stack trace analyzer", "Paste a log or trace and get a probable cause and next step."],
      ["In-app chat assistant", "Ask questions about your issues or how to use Triagey."],
    ]},
    { label: "Planning", tag: "core", items: [
      ["Kanban board", "Drag issues between open, in progress, resolved, and closed."],
      ["Sprints and milestones", "Group work into cycles and track progress toward a date."],
      ["SLA policies", "Set response and resolution targets, get flagged on breaches."],
    ]},
    { label: "Team", tag: "team", items: [
      ["Workload view", "See who's carrying how much, at a glance."],
      ["Weekly reports", "An AI-written summary of what shipped and what's piling up."],
      ["Team profiles", "Skills and current load, used to power assignee suggestions."],
    ]},
  ];
  return `
    <h1 style="margin-bottom:4px">Features</h1>
    <p class="subtle" style="margin-bottom:24px">What Triagey does, grouped by what it's for.</p>
    ${groups.map(g => `
      <div style="margin-bottom:24px">
        <div class="nav-label" style="margin:0 0 6px 2px">${g.label}</div>
        <div class="card" style="padding:2px 18px">
          ${g.items.map(([title, desc]) => `
            <div class="index-row">
              <div>
                <div class="index-title">${title}</div>
                <div class="index-desc">${desc}</div>
              </div>
              <span class="index-tag ${g.tag}">${g.label}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `).join("")}
  `;
}

function chatLogHtml() {
  if (state.chatMessages.length === 0) {
    return `<div class="subtle">Ask me anything about your issues, sprints, or how to use Triagey.</div>`;
  }
  return state.chatMessages.map(m => `
    <div style="margin-bottom:10px">
      <b>${m.role === "user" ? "You" : "Triagey AI"}:</b>
      <div>${escapeHtml(m.content)}</div>
    </div>
  `).join("");
}

function chatHtml() {
  return `
    <div class="card" style="display:flex;flex-direction:column;height:70vh">
      <h2>Chat with Triagey AI</h2>
      <div id="chatLog" style="flex:1;overflow-y:auto;margin:12px 0;padding:8px;border:1px solid var(--border,#333);border-radius:8px">
        ${chatLogHtml()}
      </div>
      <div style="display:flex;gap:8px">
        <input id="chatInput" type="text" placeholder="Ask something..." style="flex:1" onkeydown="if(event.key==='Enter') sendChatMessage()" ${state.chatSending ? "disabled" : ""} />
        <button class="btn btn-primary" onclick="sendChatMessage()" ${state.chatSending ? "disabled" : ""}>${state.chatSending ? "..." : "Send"}</button>
      </div>
    </div>
  `;
}

function toggleChatWidget() {
  state.chatWidgetOpen = !state.chatWidgetOpen;
  render();
}

function floatingChatHtml() {
  if (!state.token) return "";
  if (!state.chatWidgetOpen) {
    return `<div onclick="toggleChatWidget()" style="position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:var(--primary,#5b5bd6);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);font-size:24px;z-index:1000">&#128172;</div>`;
  }
  return `
    <div style="position:fixed;bottom:24px;right:24px;width:320px;max-height:440px;display:flex;flex-direction:column;background:var(--bg,#1e1e1e);border:1px solid var(--border,#333);border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.4);z-index:1000;overflow:hidden">
      <div style="padding:10px 14px;background:var(--primary,#5b5bd6);color:#fff;display:flex;justify-content:space-between;align-items:center">
        <b>Triagey AI</b>
        <span style="cursor:pointer" onclick="toggleChatWidget()">&times;</span>
      </div>
      <div id="chatWidgetLog" style="flex:1;overflow-y:auto;padding:10px;font-size:13px">
        ${chatLogHtml()}
      </div>
      <div style="display:flex;gap:6px;padding:10px;border-top:1px solid var(--border,#333)">
        <input id="chatWidgetInput" type="text" placeholder="Ask something..." style="flex:1" onkeydown="if(event.key==='Enter') sendChatMessage()" ${state.chatSending ? "disabled" : ""} />
        <button class="btn btn-primary" onclick="sendChatMessage()" ${state.chatSending ? "disabled" : ""}>${state.chatSending ? "..." : "Send"}</button>
      </div>
    </div>
  `;
}

async function sendChatMessage() {
  const input = document.getElementById("chatInput") || document.getElementById("chatWidgetInput");
  if (!input) return;
  const text = input.value.trim();
  if (!text || state.chatSending) return;
  state.chatMessages.push({ role: "user", content: text });
  input.value = "";
  state.chatSending = true;
  render();
  try {
    const res = await apiFetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, history: state.chatMessages.slice(-10) }),
    });
    state.chatMessages.push({ role: "assistant", content: res.reply });
  } catch (e) {
    state.chatMessages.push({ role: "assistant", content: "Sorry, I could not respond: " + e.message });
  }
  state.chatSending = false;
  render();
  setTimeout(() => {
    const log = document.getElementById("chatLog") || document.getElementById("chatWidgetLog");
    if (log) log.scrollTop = log.scrollHeight;
  }, 0);
}
















function homeHtml() {
  const s = state.stats || { total: 0, by_status: {}, overdue_count: 0 };
  return `
    <div class="home-hero">
      <h1>Your workspace at a glance</h1>
      <p class="subtle">Triagey is tracking ${s.total} issue${s.total === 1 ? "" : "s"} on this project, with AI handling the first pass on triage.</p>
    </div>
    <div class="stat-row">
      <div class="card stat-card"><div class="stat-num">${s.total}</div><div class="stat-label">Total issues</div></div>
      <div class="card stat-card"><div class="stat-num">${s.by_status.open || 0}</div><div class="stat-label">Open</div></div>
      <div class="card stat-card"><div class="stat-num">${s.by_status.resolved || 0}</div><div class="stat-label">Resolved</div></div>
      <div class="card stat-card"><div class="stat-num" style="color:${(s.overdue_count||0) > 0 ? 'var(--danger)' : 'inherit'}">${s.overdue_count || 0}</div><div class="stat-label">Overdue</div></div>
    </div>
    <div class="card" style="margin-bottom:20px;padding:2px 18px">
      <div class="index-row">
        <div><div class="index-title">Bugs &amp; Kanban</div><div class="index-desc">See and triage everything that's open right now.</div></div>
        <button class="btn" onclick="setView('issues')">Open</button>
      </div>
      <div class="index-row">
        <div><div class="index-title">Chat with Triagey AI</div><div class="index-desc">Ask about an issue, a sprint, or how something works.</div></div>
        <button class="btn btn-ai" onclick="setView('chat')">Open</button>
      </div>
      <div class="index-row">
        <div><div class="index-title">Weekly report</div><div class="index-desc">An AI-written summary of the last seven days.</div></div>
        <button class="btn" onclick="setView('reports')">Open</button>
      </div>
    </div>
    <div class="gap-8">
      <button class="btn btn-ghost" onclick="setView('about')">About Triagey</button>
      <button class="btn btn-ghost" onclick="setView('features')">All features</button>
    </div>
  `;
}
