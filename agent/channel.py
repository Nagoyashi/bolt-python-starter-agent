"""The chat-platform admin seam.

`ChannelAdmin` is what lets the agent act on *the channel it's currently in*
(set its topic/description, pin a message) without the agent core knowing it's
Slack. The Slack implementation lives in the listener layer
(`listeners/channel_admin.py`); to port to Zulip/Mattermost you write a new
adapter with these same four methods and nothing in `agent/` changes.

The critical security property: an adapter is always bound to ONE channel (the
one the message arrived in). The model is never handed a channel id and cannot
target another channel — the same "never pick the target" rule as the repo spine.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChannelAdmin(Protocol):
    """Bound to the current channel. Every method returns a short, human-readable
    result string and must not raise — platform errors come back as text the
    agent can relay."""

    def set_topic(self, topic: str) -> str:
        """Set the channel's short topic line."""
        ...

    def set_description(self, description: str) -> str:
        """Set the channel's description (a.k.a. purpose)."""
        ...

    def pin_current_message(self) -> str:
        """Pin the message that triggered this turn to the channel."""
        ...

    def unpin_current_message(self) -> str:
        """Unpin the message that triggered this turn."""
        ...
