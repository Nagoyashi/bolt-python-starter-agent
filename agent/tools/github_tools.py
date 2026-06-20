"""The agent's tools — the typed allowlist.

PROJECT_TOOLS are scoped to the one repo in ctx.deps.github (reads + the two
proposal writes). PORTFOLIO_TOOLS are read-only across all repos. Each tool
returns a string and never raises into the model: GitHub errors come back as
readable text the agent can recover from.
"""

from __future__ import annotations

from github.GithubException import GithubException
from pydantic_ai import RunContext

from agent.deps import AgentDeps
from config import ALL_REPOS
from gh import build_client


def _client(ctx: RunContext[AgentDeps]):
    if ctx.deps.github is None:
        raise RuntimeError("No repository is bound to this channel.")
    return ctx.deps.github


# ========================================================== PROJECT: reads ==
def get_status(ctx: RunContext[AgentDeps]) -> str:
    """Read this product's live status: current phase, active milestones, and how
    many ideas are waiting in the Intake queue. Use this whenever someone asks
    where the product stands."""
    try:
        s = _client(ctx).status_summary()
    except GithubException as e:
        return f"Couldn't read status: {e.data.get('message', e) if e.data else e}"

    lines = [f"Status for {s['repo']}:"]
    lines.append(f"- Current phase: {s['current_phase'] or '(see roadmap)'}")
    if s["open_milestones"]:
        for m in s["open_milestones"]:
            total = m["open"] + m["closed"]
            done = m["closed"]
            lines.append(f"- Milestone {m['title']}: {done}/{total} issues done")
    else:
        lines.append("- No open milestone right now")
    lines.append(
        f"- Intake queue: {s['proposals_total']} proposal(s) "
        f"({s['proposals_phase']} phase, {s['proposals_feature']} feature)"
    )
    return "\n".join(lines)


def list_proposals(ctx: RunContext[AgentDeps]) -> str:
    """List the open ideas in the Intake queue (proposals waiting for Robert to
    triage). Use before filing a new one to avoid duplicates."""
    try:
        items = _client(ctx).list_proposals()
    except GithubException as e:
        return f"Couldn't read the queue: {e}"
    if not items:
        return "The Intake queue is empty — no proposals filed yet."
    out = [f"Intake queue ({len(items)} open):"]
    for p in items:
        out.append(f"#{p['number']} [{p['kind']}] {p['title']} — {p['comments']} comment(s)")
    return "\n".join(out)


def get_proposal(ctx: RunContext[AgentDeps], number: int) -> str:
    """Read one proposal (or any issue) in full, including its discussion."""
    try:
        issue = _client(ctx).get_issue(number)
    except GithubException as e:
        return f"Couldn't read #{number}: {e}"
    if issue is None:
        return f"No issue #{number} in this repo."
    parts = [
        f"#{issue['number']} {issue['title']} ({issue['state']})",
        f"Labels: {', '.join(issue['labels']) or 'none'}",
        "",
        issue["body"] or "(no description)",
    ]
    if issue["comments"]:
        parts.append("\nDiscussion:")
        for c in issue["comments"]:
            parts.append(f"- {c['author']}: {c['body']}")
    return "\n".join(parts)


def read_roadmap(ctx: RunContext[AgentDeps]) -> str:
    """Read project.md — the product's phase-level roadmap. Read this before
    helping map a new phase or feature so your questions fit what already exists."""
    try:
        md = _client(ctx).read_file("project.md")
    except GithubException as e:
        return f"Couldn't read project.md: {e}"
    return md or "No project.md found in this repo yet."


def list_releases(ctx: RunContext[AgentDeps]) -> str:
    """List the most recent releases that have shipped for this product."""
    try:
        rels = _client(ctx).recent_releases()
    except GithubException as e:
        return f"Couldn't read releases: {e}"
    if not rels:
        return "No releases published yet."
    return "Recent releases:\n" + "\n".join(
        f"- {r['tag']} — {r['name']} ({r['published_at']})" for r in rels
    )


# ========================================================= PROJECT: writes ==
def _build_proposal_body(
    actor: str,
    problem: str,
    audience: str,
    why_now: str,
    rough_scope: str,
    open_questions: str,
) -> str:
    def field(v: str) -> str:
        return v.strip() if v and v.strip() else "_(not specified)_"

    return (
        f"## Problem\n{field(problem)}\n\n"
        f"## Who it's for\n{field(audience)}\n\n"
        f"## Why now\n{field(why_now)}\n\n"
        f"## Rough scope\n{field(rough_scope)}\n\n"
        f"## Open questions\n{field(open_questions)}\n\n"
        f"---\n*Filed via Slack by <@{actor}>. Uncommitted — awaiting triage.*"
    )


def create_proposal(
    ctx: RunContext[AgentDeps],
    title: str,
    kind: str,
    problem: str,
    audience: str = "",
    why_now: str = "",
    rough_scope: str = "",
    open_questions: str = "",
) -> str:
    """File a new idea into the Intake queue. ONLY call this after you've talked
    the idea through with the person and reflected it back — the goal is a
    triage-ready writeup, not a one-liner. Never invent facts or numbers to fill
    the fields; leave a field blank if it's genuinely unknown.

    Args:
        title: A short, specific title.
        kind: "phase" for a proposed product phase, or "feature" for a feature.
        problem: The problem this solves (required).
        audience: Who it's for.
        why_now: Why it matters now / how it fits the roadmap.
        rough_scope: A rough sense of size or what's involved.
        open_questions: Anything still uncertain.
    """
    kind = kind.lower().strip()
    if kind not in ("phase", "feature"):
        return "kind must be 'phase' or 'feature'."
    body = _build_proposal_body(
        ctx.deps.actor, problem, audience, why_now, rough_scope, open_questions
    )
    try:
        url = _client(ctx).create_proposal(title=title, kind=kind, body=body)
    except GithubException as e:
        return f"Couldn't file the proposal: {e}"
    return f"Filed as a {kind} proposal: {url}\nIt's now in Robert's Intake queue."


def comment_on_proposal(ctx: RunContext[AgentDeps], number: int, comment: str) -> str:
    """Add a comment to an existing proposal — e.g. to capture more thinking from
    the discussion onto the right issue."""
    try:
        url = _client(ctx).comment(number, comment)
    except GithubException as e:
        return f"Couldn't comment on #{number}: {e}"
    return f"Added to #{number}: {url}"


# ======================================================== PORTFOLIO: reads ==
def get_portfolio_status(ctx: RunContext[AgentDeps]) -> str:
    """Read live status across ALL products at once, for a cross-project overview."""
    blocks = []
    for repo in ALL_REPOS:
        try:
            s = build_client(repo).status_summary()
            phase = s["current_phase"] or "(see roadmap)"
            ms = ", ".join(
                f"{m['title']} {m['closed']}/{m['open'] + m['closed']}"
                for m in s["open_milestones"]
            ) or "no open milestone"
            blocks.append(
                f"*{repo.name}* — phase: {phase}; {ms}; "
                f"{s['proposals_total']} proposal(s) in queue"
            )
        except GithubException as e:
            blocks.append(f"*{repo.name}* — couldn't read ({e})")
    return "Portfolio overview:\n" + "\n".join(f"- {b}" for b in blocks)


PROJECT_TOOLS = [
    get_status,
    list_proposals,
    get_proposal,
    read_roadmap,
    list_releases,
    create_proposal,
    comment_on_proposal,
]

PORTFOLIO_TOOLS = [get_portfolio_status]
