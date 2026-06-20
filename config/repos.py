"""Channel -> repository binding.

This is the security spine of the whole app: the agent NEVER chooses which repo
to act on. The repo is resolved here, from the Slack channel the message arrived
in, and injected into the agent's deps. A prompt-injected message in #cutecumber
physically cannot touch sabevalor, because the model is never handed sabevalor's
client.

Fill in the four channel IDs and the portfolio channel ID below. To get a
channel's ID in Slack: open the channel -> click its name -> scroll to the
bottom of the "About" tab -> "Channel ID" (looks like C0123456789).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Repo:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


# --- The product repos. Confirm the owner + exact repo names. ----------------
SABEVALOR = Repo(owner="Nagoyashi", name="sabevalor")
SPREADSHEETMILLIONAIRE = Repo(owner="Nagoyashi", name="spreadsheet-millionaire")
CUTECUMBER = Repo(owner="Nagoyashi", name="cutecumber")
PANDAVO = Repo(owner="Nagoyashi", name="pandavo")  # new one — fix the slug if different
ROBPERSONALWEBSITE = Repo(owner="Nagoyashi", name="robpersonalwebsite")
VOUND = Repo(owner="Nagoyashi", name="vound")

ALL_REPOS: list[Repo] = [
    SABEVALOR,
    SPREADSHEETMILLIONAIRE,
    CUTECUMBER,
    PANDAVO,
    ROBPERSONALWEBSITE,
    VOUND,
]


# --- Wire each Slack channel to its repo. Replace the placeholder IDs. -------
CHANNEL_REPOS: dict[str, Repo] = {
    "C0BC2U9CA2G": SABEVALOR,           # #sabevalor
    "C0BCTHR4GNL": SPREADSHEETMILLIONAIRE,  # #spreadsheetmillionaire
    "C0BCTJ07XK2": CUTECUMBER,          # #cutecumber
    "C0BBHR26CET": PANDAVO,             # #pandavo
    "C0BBX3TDWP7": ROBPERSONALWEBSITE,  # #personalwebsite
    "C0BBYDE37V4": VOUND,               # #csmtooling
}

# Read-only cross-project rollup channel (e.g. #portfolio).
PORTFOLIO_CHANNEL_ID: str = "C0BC2UE3KAQ"  # #portfolio


def resolve(channel_id: str, *, is_dm: bool = False) -> tuple[str, Repo | None]:
    """Map a channel to (mode, repo).

    mode is one of:
      - "project"   -> scoped to a single repo (read + propose)
      - "portfolio" -> cross-project read-only rollup
      - "unknown"   -> channel isn't wired to anything
    DMs default to the portfolio (general overview / onboarding) experience.
    """
    if channel_id == PORTFOLIO_CHANNEL_ID:
        return "portfolio", None
    if channel_id in CHANNEL_REPOS:
        return "project", CHANNEL_REPOS[channel_id]
    if is_dm:
        return "portfolio", None
    return "unknown", None
