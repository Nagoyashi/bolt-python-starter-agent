"""Channel-admin tools — the agent acting on the channel it's in.

These never target an arbitrary channel: they call ctx.deps.channel, which the
listener bound to the current channel before the run started. Available in both
project and portfolio channels; absent (None) in unknown channels and where no
channel admin was injected.
"""

from __future__ import annotations

from pydantic_ai import RunContext

from agent.deps import AgentDeps

_NO_CHANNEL = "I can't manage this channel here."


def set_channel_description(ctx: RunContext[AgentDeps], description: str) -> str:
    """Set THIS channel's description (its 'purpose' — the longer blurb under the
    channel name). Confirm the exact wording with the person before changing it,
    since it's visible to everyone in the channel.

    Args:
        description: The new channel description text.
    """
    if ctx.deps.channel is None:
        return _NO_CHANNEL
    return ctx.deps.channel.set_description(description)


def set_channel_topic(ctx: RunContext[AgentDeps], topic: str) -> str:
    """Set THIS channel's topic (the short line beside the channel name). Confirm
    the wording first — it's visible to everyone.

    Args:
        topic: The new channel topic text.
    """
    if ctx.deps.channel is None:
        return _NO_CHANNEL
    return ctx.deps.channel.set_topic(topic)


def pin_message(ctx: RunContext[AgentDeps]) -> str:
    """Pin the current message to this channel — use when someone says to pin
    'this' (the message they just sent in the thread)."""
    if ctx.deps.channel is None:
        return _NO_CHANNEL
    return ctx.deps.channel.pin_current_message()


def unpin_message(ctx: RunContext[AgentDeps]) -> str:
    """Unpin the current message from this channel."""
    if ctx.deps.channel is None:
        return _NO_CHANNEL
    return ctx.deps.channel.unpin_current_message()


CHANNEL_TOOLS = [
    set_channel_description,
    set_channel_topic,
    pin_message,
    unpin_message,
]
