"""The only module in the app that talks to GitHub.

Single responsibility, swappable, testable. It exposes exactly two kinds of
operation:

  READS   — status, the proposal queue, a specific issue, project.md, releases
  WRITES  — create a `proposal` issue, comment on one  (THAT IS THE WHOLE WRITE
            SURFACE)

There is no method to merge, tag, deploy, assign milestones, or edit code,
because those are Robert's gated steps and the agent must never perform them.
If you ever need the agent to do more, you add a method here on purpose — the
allowlist lives in one file you can read top to bottom.
"""

from __future__ import annotations

from functools import lru_cache

from github import Github
from github.GithubException import GithubException, UnknownObjectException

from config import Repo
from gh.tokens import get_github

LABEL_PROPOSAL = "proposal"
VALID_KINDS = ("phase", "feature")

# name -> (hex color, description) for the labels the Intake queue relies on.
_DESIRED_LABELS = {
    LABEL_PROPOSAL: ("0E8A16", "Uncommitted idea awaiting triage"),
    "type:phase": ("1D76DB", "Proposed product phase"),
    "type:feature": ("5319E7", "Proposed feature"),
}

_MAX_BODY = 4000
_MAX_COMMENTS = 10


class GitHubClient:
    """A read + bounded-write client scoped to ONE repository."""

    def __init__(self, full_name: str, gh: Github):
        self._full_name = full_name
        self._repo = gh.get_repo(full_name)

    @property
    def full_name(self) -> str:
        return self._full_name

    # ---------------------------------------------------------------- reads --
    def status_summary(self) -> dict:
        """High-level state: open milestones (= active phases) + proposal counts."""
        milestones = []
        for m in self._repo.get_milestones(state="open"):
            milestones.append(
                {"title": m.title, "open": m.open_issues, "closed": m.closed_issues}
            )

        proposals = self.list_proposals()
        phases = sum(1 for p in proposals if p["kind"] == "phase")
        features = sum(1 for p in proposals if p["kind"] == "feature")

        roadmap = self.read_file("project.md")
        current_phase = _extract_current_phase(roadmap) if roadmap else None

        return {
            "repo": self._full_name,
            "current_phase": current_phase,
            "open_milestones": milestones,
            "proposals_total": len(proposals),
            "proposals_phase": phases,
            "proposals_feature": features,
        }

    def list_proposals(self, limit: int = 50) -> list[dict]:
        """Open issues in the Intake queue (label:proposal)."""
        try:
            label = self._repo.get_label(LABEL_PROPOSAL)
        except UnknownObjectException:
            return []  # label not created yet => no proposals filed yet

        out: list[dict] = []
        for issue in self._repo.get_issues(state="open", labels=[label]):
            if issue.pull_request is not None:
                continue
            names = {lbl.name for lbl in issue.labels}
            kind = (
                "phase" if "type:phase" in names
                else "feature" if "type:feature" in names
                else "unspecified"
            )
            out.append(
                {
                    "number": issue.number,
                    "title": issue.title,
                    "kind": kind,
                    "url": issue.html_url,
                    "comments": issue.comments,
                }
            )
            if len(out) >= limit:
                break
        return out

    def get_issue(self, number: int) -> dict | None:
        try:
            issue = self._repo.get_issue(number)
        except UnknownObjectException:
            return None
        comments = [
            {"author": c.user.login if c.user else "?", "body": (c.body or "")[:1000]}
            for c in list(issue.get_comments())[-_MAX_COMMENTS:]
        ]
        return {
            "number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "labels": [lbl.name for lbl in issue.labels],
            "body": (issue.body or "")[:_MAX_BODY],
            "url": issue.html_url,
            "comments": comments,
        }

    def read_file(self, path: str) -> str | None:
        try:
            content = self._repo.get_contents(path)
        except UnknownObjectException:
            return None
        if isinstance(content, list):  # it's a directory
            return "\n".join(sorted(c.name for c in content))
        try:
            return content.decoded_content.decode("utf-8")[:_MAX_BODY * 2]
        except Exception:
            return None

    def recent_releases(self, limit: int = 5) -> list[dict]:
        out: list[dict] = []
        for r in self._repo.get_releases()[:limit]:
            out.append(
                {
                    "tag": r.tag_name,
                    "name": r.title or r.tag_name,
                    "published_at": str(r.published_at) if r.published_at else "draft",
                    "url": r.html_url,
                }
            )
        return out

    # --------------------------------------------------------------- writes --
    def create_proposal(self, title: str, kind: str, body: str) -> str:
        """Create a `proposal` issue (no milestone) and return its URL."""
        if kind not in VALID_KINDS:
            raise ValueError(f"kind must be one of {VALID_KINDS}, got {kind!r}")
        self.ensure_labels()
        issue = self._repo.create_issue(title=title, body=body)
        issue.add_to_labels(LABEL_PROPOSAL, f"type:{kind}")
        return issue.html_url

    def comment(self, number: int, text: str) -> str:
        issue = self._repo.get_issue(number)
        return issue.create_comment(text).html_url

    def ensure_labels(self) -> None:
        existing = {lbl.name for lbl in self._repo.get_labels()}
        for name, (color, desc) in _DESIRED_LABELS.items():
            if name not in existing:
                try:
                    self._repo.create_label(name=name, color=color, description=desc)
                except GithubException:
                    pass  # raced or insufficient perms; not fatal for reads


@lru_cache(maxsize=16)
def build_client(repo: Repo) -> GitHubClient:
    """Cached client factory. One PyGithub auth shared across all repos."""
    return GitHubClient(repo.full_name, get_github())


def _extract_current_phase(markdown: str) -> str | None:
    """Best-effort: pull the 'current phase' line out of project.md."""
    lines = markdown.splitlines()
    for i, line in enumerate(lines):
        if "current phase" in line.lower():
            cleaned = line.lstrip("#*->| ").strip()
            if cleaned and ":" in cleaned:
                return cleaned
            # otherwise look at the next non-empty line
            for nxt in lines[i + 1 : i + 4]:
                if nxt.strip():
                    return nxt.lstrip("#*->| ").strip()
            return cleaned or None
    return None
