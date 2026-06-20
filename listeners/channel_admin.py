"""Slack implementation of the agent's ChannelAdmin seam.

This is the only place channel-management touches Slack. It is constructed by the
event listeners, bound to the single channel (and triggering message) the event
arrived in, and injected into the agent's deps. The agent can therefore only ever
edit the channel it's already in — it never sees a channel id.

Errors are swallowed into readable strings: tools must not raise into the model.
"""

from __future__ import annotations

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _reason(e: SlackApiError) -> str:
    err = e.response.get("error", "unknown_error") if e.response else "unknown_error"
    hints = {
        "missing_scope": "the app is missing a required scope (reinstall needed)",
        "not_in_channel": "I'm not a member of this channel — invite me first",
        "channel_not_found": "I can't see this channel",
        "restricted_action": "a workspace setting blocks this action",
        "no_permission": "I don't have permission for this",
        "method_not_supported_for_channel_type": "this isn't supported here (e.g. a DM)",
        "no_pin": "that message isn't pinned",
        "already_pinned": "that message is already pinned",
    }
    return hints.get(err, err)


class SlackChannelAdmin:
    """A ChannelAdmin bound to one Slack channel + the triggering message ts."""

    def __init__(self, client: WebClient, channel_id: str, message_ts: str | None):
        self._client = client
        self._channel = channel_id
        self._ts = message_ts

    def set_topic(self, topic: str) -> str:
        try:
            self._client.conversations_setTopic(channel=self._channel, topic=topic)
        except SlackApiError as e:
            return f"Couldn't set the topic: {_reason(e)}."
        return f"Done — channel topic is now: {topic}"

    def set_description(self, description: str) -> str:
        try:
            self._client.conversations_setPurpose(
                channel=self._channel, purpose=description
            )
        except SlackApiError as e:
            return f"Couldn't set the description: {_reason(e)}."
        return f"Done — channel description is now: {description}"

    def pin_current_message(self) -> str:
        if not self._ts:
            return "There's no specific message here for me to pin."
        try:
            self._client.pins_add(channel=self._channel, timestamp=self._ts)
        except SlackApiError as e:
            return f"Couldn't pin the message: {_reason(e)}."
        return "Pinned this message to the channel."

    def unpin_current_message(self) -> str:
        if not self._ts:
            return "There's no specific message here for me to unpin."
        try:
            self._client.pins_remove(channel=self._channel, timestamp=self._ts)
        except SlackApiError as e:
            return f"Couldn't unpin the message: {_reason(e)}."
        return "Unpinned this message."
