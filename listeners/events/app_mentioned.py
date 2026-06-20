import re
from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from agent import run_agent
from listeners.channel_admin import SlackChannelAdmin
from listeners.views.feedback_builder import build_feedback_blocks
from thread_context import conversation_store

_LOADING = [
    "Reading the project board…",
    "Checking the roadmap…",
    "Pulling live status from GitHub…",
    "Thinking it through…",
]


def handle_app_mentioned(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle @mentions in channels — routed to the channel's project agent."""
    try:
        channel_id = context.channel_id
        thread_ts = event.get("thread_ts") or event["ts"]
        cleaned_text = re.sub(r"<@[A-Z0-9]+>", "", event.get("text", "")).strip()

        if not cleaned_text:
            say(text="Hey! Ask me where the product stands, or let's map out an idea.",
                thread_ts=thread_ts)
            return

        set_status(status="Thinking...", loading_messages=_LOADING)

        history = conversation_store.get_history(channel_id, thread_ts)
        result = run_agent(
            channel_id,
            cleaned_text,
            history=history,
            is_dm=False,
            actor=context.user_id,
            channel_admin=SlackChannelAdmin(client, channel_id, event["ts"]),
        )

        streamer = say_stream()
        streamer.append(markdown_text=result.output)
        streamer.stop(blocks=build_feedback_blocks())

        conversation_store.set_history(channel_id, thread_ts, result.all_messages())

    except Exception as e:
        logger.exception(f"Failed to handle app mention: {e}")
        say(text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event["ts"])
