"""run_agent — the one function every chat adapter calls.

It is platform-agnostic: channel id + text + history in, reply text + new history
out. The Slack listeners are the adapter that calls this. To port to another
chat platform you write a new adapter that calls this same function; nothing in
agent/ or gh/ changes.
"""

from __future__ import annotations

from agent.agents import get_model, portfolio_agent, project_agent
from agent.deps import AgentDeps
from config import resolve
from gh import build_client

_UNKNOWN_REPLY = (
    "This channel isn't wired to a product yet, so I can't read or propose "
    "anything here. Try one of the product channels, or #portfolio for an overview."
)


class _StaticResult:
    """Minimal result shim so adapters can treat every reply uniformly."""

    def __init__(self, text: str, history):
        self._text = text
        self._history = history or []

    @property
    def output(self) -> str:
        return self._text

    def all_messages(self):
        return self._history


def run_agent(
    channel_id: str,
    text: str,
    history=None,
    *,
    is_dm: bool = False,
    actor: str = "",
    channel_admin=None,
):
    """Resolve the channel, run the appropriate agent, return its result.

    channel_admin is an optional ChannelAdmin bound to this channel (built by the
    listener) so the agent can manage the channel it's in. It is injected for
    wired channels only — never for unknown channels.
    """
    mode, repo = resolve(channel_id, is_dm=is_dm)

    if mode == "unknown":
        return _StaticResult(_UNKNOWN_REPLY, history)

    if mode == "portfolio":
        deps = AgentDeps(mode="portfolio", actor=actor, channel=channel_admin)
        return portfolio_agent.run_sync(
            text, model=get_model(), deps=deps, message_history=history
        )

    # mode == "project"
    deps = AgentDeps(
        mode="project",
        actor=actor,
        repo=repo,
        github=build_client(repo),
        channel=channel_admin,
    )
    return project_agent.run_sync(
        text, model=get_model(), deps=deps, message_history=history
    )
