"""What the agent is handed for a single run.

Note what is NOT here: no Slack client, no Slack types. The agent core knows
nothing about the chat platform — that's the seam that lets you swap Slack for
Zulip/Mattermost later by rewriting only the listener adapter. `channel` is the
one platform touch-point, and even it is an abstract interface (agent/channel.py),
not a Slack object.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.channel import ChannelAdmin
from config import Repo
from gh import GitHubClient


@dataclass
class AgentDeps:
    mode: str                       # "project" | "portfolio"
    actor: str                      # who is asking (user id), for logging only
    repo: Repo | None = None        # set in project mode
    github: GitHubClient | None = None  # the scoped client, set in project mode
    channel: ChannelAdmin | None = None  # bound to the current channel, if any
