import os
import json
from typing import List, Optional

from google import genai
from dotenv import load_dotenv

load_dotenv()

_client: Optional["genai.Client"] = None
MODEL = "gemini-3.6-flash"


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("paste-your-real-key"):
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add a real key to backend/.env"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _generate(prompt: str, max_tokens: int = 500, system: Optional[str] = None) -> str:
    """Call Gemini with a single prompt and return the text response."""
    client = get_client()
    from google.genai import types

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens * 2,
        system_instruction=system,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config,
    )
    text = response.text
    if not text:
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception:
            text = ""
    return text or ""


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in AI response: {text[:200]}")
    return json.loads(text[start : end + 1])


def _extract_json_array(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []


def triage_issue(title: str, description: str) -> dict:
    prompt = f"""You are a bug-tracking triage assistant. Classify the following issue report.

Title: {title}
Description: {description or "(no description provided)"}

Respond with ONLY a JSON object (no other text, no markdown fences) in this exact shape:
{{
  "priority": "low" | "medium" | "high" | "critical",
  "severity": one short phrase describing real-world impact,
  "issue_type": "bug" | "feature" | "task" | "question",
  "tags": array of 2-5 short lowercase keyword tags,
  "summary": one concise sentence summarizing the issue for a busy engineer,
  "confidence": "low" | "medium" | "high" (your confidence in this classification)
}}"""
    text = _generate(prompt, max_tokens=500)
    data = _extract_json(text)
    data.setdefault("priority", "medium")
    data.setdefault("severity", "")
    data.setdefault("issue_type", "bug")
    data.setdefault("tags", [])
    data.setdefault("summary", "")
    data.setdefault("confidence", "medium")
    return data


def find_duplicates(new_title: str, new_description: str, existing_issues: List[dict]) -> List[dict]:
    if not existing_issues:
        return []
    issues_block = "\n".join(
        f'- id={i["id"]} #{i["number"]}: "{i["title"]}" - {(i.get("description") or "")[:200]}'
        for i in existing_issues
    )
    prompt = f"""You are helping detect duplicate bug reports.

NEW ISSUE:
Title: {new_title}
Description: {new_description or "(none)"}

EXISTING OPEN ISSUES:
{issues_block}

Which existing issues, if any, are likely duplicates of the new issue? Consider issues
duplicates if they describe the same underlying problem, even with different wording.

Respond with ONLY a JSON array (no other text, no markdown fences). Each element:
{{"issue_id": <int>, "confidence": "low"|"medium"|"high", "reason": "<one short sentence>"}}

Only include issues with medium or high confidence. Return [] if there are no likely duplicates."""
    text = _generate(prompt, max_tokens=500)
    candidates = _extract_json_array(text)

    by_id = {i["id"]: i for i in existing_issues}
    results = []
    for c in candidates:
        issue = by_id.get(c.get("issue_id"))
        if not issue:
            continue
        results.append({
            "issue_id": issue["id"],
            "number": issue["number"],
            "title": issue["title"],
            "confidence": c.get("confidence", "medium"),
            "reason": c.get("reason", ""),
        })
    return results


def suggest_response(issue_title: str, issue_description: str, comments: List[str]) -> str:
    thread = "\n".join(f"- {c}" for c in comments) if comments else "(no comments yet)"
    prompt = f"""You are an engineering assistant helping triage a tracked issue.

Title: {issue_title}
Description: {issue_description}

Comment thread so far:
{thread}

Write a short (3-5 sentence) helpful comment suggesting likely root cause(s) and a
concrete next debugging step. Be specific and practical. Do not use markdown headers."""
    return _generate(prompt, max_tokens=400).strip()


def suggest_code_fix(issue_title: str, issue_description: str, comments: List[str]) -> str:
    thread = "\n".join(f"- {c}" for c in comments) if comments else "(no comments yet)"
    prompt = f"""You are a senior software engineer helping fix a tracked bug.

Title: {issue_title}
Description: {issue_description}

Comment thread so far:
{thread}

Since you do not have access to the actual codebase, suggest a plausible, illustrative
code-level fix for this kind of issue. Include a short explanation (2-3 sentences) followed
by one fenced code block (triple backticks with a language hint) showing example code that
addresses the likely root cause. Keep the whole response under 200 words. Make clear this
is an illustrative example, not a guaranteed fix, since you cannot see the real code."""
    return _generate(prompt, max_tokens=500).strip()


def generate_weekly_report(project_name, created_issues, resolved_issues, comments_count, top_tags):
    created_list = "\n".join(f"- [{i['priority']}] {i['title']}" for i in created_issues) or "(none)"
    resolved_list = "\n".join(f"- {i['title']}" for i in resolved_issues) or "(none)"
    tags_str = ", ".join(top_tags) if top_tags else "(none)"
    prompt = f"""You are writing a weekly engineering status update for the project "{project_name}".

Issues created this week:
{created_list}

Issues resolved this week:
{resolved_list}

Comments posted this week: {comments_count}
Most common tags: {tags_str}

Write a concise weekly report (150-200 words) for a team lead: overall trend, notable
issues, and one suggested focus area for next week. Plain prose, no markdown headers."""
    return _generate(prompt, max_tokens=500).strip()


def suggest_assignee(issue_title: str, issue_description: str, candidates: List[dict]) -> dict:
    candidates_str = "\n".join(
        f'- id={c["id"]} username={c["username"]} currently has {c["open_count"]} open/in-progress issues'
        for c in candidates
    )
    prompt = f"""You are helping assign a bug/issue to the best team member.

Issue: {issue_title}
Description: {issue_description or "(none)"}

Team members and current workload:
{candidates_str}

Pick the single best person to assign this to, balancing relevant fit and current workload
(prefer less-loaded people when fit is similar). Respond with ONLY a JSON object, no other
text: {{"user_id": <int>, "username": "<string>", "reason": "<one short sentence>"}}"""
    text = _generate(prompt, max_tokens=200)
    return _extract_json(text)


def summarize_activity(project_name, activity_items):
    lines = "\n".join(f'- [{a["type"]}] {a["text"]} ({a["when"]})' for a in activity_items) or "(no recent activity)"
    prompt = f"""You are summarizing recent activity for the project "{project_name}" for a team member catching up.

Recent activity (most recent first):
{lines}

Write a short summary (100-150 words) covering what's been happening: notable issues,
patterns, and anything that needs attention. Plain prose, no markdown headers."""
    return _generate(prompt, max_tokens=400).strip()


def sprint_copilot_chat(sprint_context, chat_history, question):
    history_block = "\n".join(
        f'{"User" if m["role"] == "user" else "Assistant"}: {m["text"]}' for m in chat_history
    )
    system_prompt = f"""You are a sprint assistant with access to this sprint's data:

{sprint_context}

Answer questions about this sprint concisely and specifically, referencing the actual
issues/data given. If asked something the data doesn't cover, say so honestly. Keep
answers under 100 words unless more detail is clearly needed."""
    full_prompt = f"{history_block}\n\nUser: {question}" if history_block else question
    return _generate(full_prompt, max_tokens=400, system=system_prompt).strip()


def analyze_sprint_risk(sprint_name, goal, days_remaining, total_issues, resolved_issues, open_issues_summary):
    issues_block = "\n".join(
        f'- [{i["priority"]}] {i["title"]} (status: {i["status"]})' for i in open_issues_summary
    ) or "(no open issues)"
    prompt = f"""You are an engineering delivery risk analyst for a sprint.

Sprint: {sprint_name}
Goal: {goal or "(no goal set)"}
Days remaining: {days_remaining}
Total issues in sprint: {total_issues}
Resolved so far: {resolved_issues}

Open/unresolved issues:
{issues_block}

Estimate the probability (0-100) that this sprint will NOT be completed on time, given
the remaining work and time left. Respond with ONLY a JSON object, no other text:
{{"risk_percent": <int 0-100>, "reasoning": "<1-2 short sentences>", "recommendation": "<one short actionable sentence>"}}"""
    text = _generate(prompt, max_tokens=300)
    return _extract_json(text)


def plan_sprint(sprint_name, goal, capacity_hint, backlog_issues):
    issues_block = "\n".join(
        f'- id={i["id"]} #{i["number"]} [{i["priority"]}] "{i["title"]}"' for i in backlog_issues
    ) or "(no backlog issues available)"
    prompt = f"""You are planning a sprint.

Sprint: {sprint_name}
Goal: {goal or "(none set)"}
Capacity note: {capacity_hint}

Backlog issues not yet in any sprint:
{issues_block}

Select which issues should go into this sprint, prioritizing high-priority items and a
reasonable, achievable scope. Respond with ONLY a JSON object, no other text:
{{"selected_issue_ids": [<int>, ...], "reasoning": "<1-2 sentences explaining the picks>"}}"""
    text = _generate(prompt, max_tokens=400)
    return _extract_json(text)


def analyze_stack_trace(issue_title, stack_trace):
    prompt = f"""You are debugging a software issue.

Issue: {issue_title}

Stack trace / error log:
{stack_trace}

Analyze this and respond with ONLY a JSON object, no other text:
{{"probable_cause": "<1-2 sentences on the likely root cause>", "recommendation": "<one concrete next debugging step>"}}"""
    text = _generate(prompt, max_tokens=400)
    return _extract_json(text)


def compare_assignee_candidates(issue_title, issue_description, candidates):
    candidates_str = "\n".join(
        f'- id={c["id"]} username={c["username"]}: skills={c.get("skills", [])}, '
        f'specialization="{c.get("specialization", "")}", experience={c.get("experience_years", 0)}yrs, '
        f'active_issues={c.get("active_issue_count", 0)}, resolved={c.get("resolved_issue_count", 0)}'
        for c in candidates
    )
    prompt = f"""You are scoring candidates to assign a bug/issue to, based on fit and workload.

Issue: {issue_title}
Description: {issue_description or "(none)"}

Candidates:
{candidates_str}

Score each candidate 0-100 on overall fit, weighing skill/specialization match, experience,
and current workload (fewer active issues is better). Respond with ONLY a JSON array, no
other text. Each element:
{{"user_id": <int>, "username": "<string>", "score": <int 0-100>, "reason": "<one short sentence>"}}

Order the array from best to worst match."""
    text = _generate(prompt, max_tokens=500)
    return _extract_json_array(text)


def estimate_issue_metrics(issue_title, issue_description, priority, comments):
    thread = "\n".join(f"- {c}" for c in comments) if comments else "(no comments yet)"
    prompt = f"""You are estimating metrics for a tracked bug/issue.

Title: {issue_title}
Description: {issue_description or "(none)"}
Priority: {priority}
Comments so far:
{thread}

Estimate two things and respond with ONLY a JSON object, no other text:
{{"frustration_score": <int 0-100, how frustrated/urgent the reporter likely feels based on
  the description tone and priority>, "predicted_fix_hours": <number, rough estimate of hours
  to fix based on the description complexity>}}"""
    text = _generate(prompt, max_tokens=200)
    return _extract_json(text)








def chat_reply(message: str, history: list = None) -> str:
    """General-purpose in-app assistant for Triagey."""
    history = history or []
    convo = "\n".join(f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-10:])
    prompt = f"{convo}\nuser: {message}\nassistant:" if convo else f"user: {message}\nassistant:"
    system = (
        "You are the in-app assistant for Triagey, a bug/issue tracking tool. "
        "Help users with questions about bugs, workflow, and using the app. "
        "Keep answers short and friendly. Do not use markdown headers."
    )
    return _generate(prompt, max_tokens=400, system=system)
