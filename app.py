import logging
import os

from dotenv import load_dotenv

# Load .env BEFORE importing `agent`: the agents are constructed at import time
# and call get_model(), which reads ANTHROPIC_API_KEY from the environment.
load_dotenv(dotenv_path=".env", override=False)

from slack_bolt import App  # noqa: E402
from slack_bolt.adapter.socket_mode import SocketModeHandler  # noqa: E402
from slack_sdk import WebClient  # noqa: E402

from agent import get_model  # noqa: E402
from listeners import register_listeners  # noqa: E402

get_model()  # Fail fast if no AI provider key is configured

logging.basicConfig(level=logging.INFO)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    client=WebClient(
        base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
        token=os.environ.get("SLACK_BOT_TOKEN"),
    ),
)

register_listeners(app)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
