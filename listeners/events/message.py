from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from agent import run_agent
from listeners.views.feedback_builder import build_feedback_blocks
from thread_context import conversation_store

_LOADING = [
    "Reading the project board…",
    "Checking the roadmap…",
    "Pulling live status from GitHub…",
    "Thinking it through…",
]


def handle_message(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle DMs (portfolio overview) and replies in threads the bot is in."""
    if event.get("subtype") or event.get("bot_id"):
        return

    is_dm = event.get("channel_type") == "im"
    is_thread_reply = event.get("thread_ts") is not None

    if is_dm:
        pass
    elif is_thread_reply:
        # Only continue a channel thread the bot is already engaged in.
        if conversation_store.get_history(context.channel_id, event["thread_ts"]) is None:
            return
    else:
        # Top-level channel messages are handled by app_mentioned.
        return

    try:
        channel_id = context.channel_id
        thread_ts = event.get("thread_ts") or event["ts"]

        set_status(status="Thinking...", loading_messages=_LOADING)

        history = conversation_store.get_history(channel_id, thread_ts)
        result = run_agent(
            channel_id,
            event.get("text", ""),
            history=history,
            is_dm=is_dm,
            actor=context.user_id,
        )

        streamer = say_stream()
        streamer.append(markdown_text=result.output)
        streamer.stop(blocks=build_feedback_blocks())

        conversation_store.set_history(channel_id, thread_ts, result.all_messages())

    except Exception as e:
        logger.exception(f"Failed to handle message: {e}")
        say(text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event.get("ts"))
