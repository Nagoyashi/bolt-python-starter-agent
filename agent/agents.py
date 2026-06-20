"""Two agents, two tool surfaces — the security boundary expressed in code.

- project_agent  has the read tools AND the two proposal-write tools, and only
  ever sees one repo (via deps).
- portfolio_agent has only the read-only rollup tool — no GitHub write tool is
  registered on it, so it cannot create or change anything in any repo.

Both also get CHANNEL_TOOLS (manage the current Slack channel's topic/description
and pins). That is a Slack-only capability bound to the current channel; it does
not touch GitHub, so the "portfolio can't write to repos" guarantee stands.

The listener picks which one to run based on the channel. There is no path by
which a portfolio conversation gains repo-write power, or a project conversation
reaches another repo.
"""

from __future__ import annotations

import os

from pydantic_ai import Agent, RunContext

from agent.deps import AgentDeps
from agent.prompts import PORTFOLIO_SYSTEM_PROMPT, PROJECT_SYSTEM_PROMPT
from agent.tools import CHANNEL_TOOLS, PORTFOLIO_TOOLS, PROJECT_TOOLS

_cached_model: str | None = None


def get_model() -> str:
    """Pick the model from available keys. Prefers Anthropic.

    Haiku 4.5 is the default: cheap and fast for high-volume cofounder chat and
    status reads. For sharper strategic reasoning in the phase/feature mapping
    flow, swap to 'anthropic:claude-sonnet-4-6' or 'anthropic:claude-opus-4-8'.
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    if os.environ.get("ANTHROPIC_API_KEY"):
        _cached_model = "anthropic:claude-haiku-4-5"
    elif os.environ.get("OPENAI_API_KEY"):
        _cached_model = "openai:gpt-4.1-mini"
    else:
        raise RuntimeError(
            "No AI provider configured. Set ANTHROPIC_API_KEY (or OPENAI_API_KEY)."
        )
    return _cached_model


project_agent = Agent(
    get_model(),
    deps_type=AgentDeps,
    system_prompt=PROJECT_SYSTEM_PROMPT,
    tools=PROJECT_TOOLS + CHANNEL_TOOLS,
)


@project_agent.system_prompt
def _which_product(ctx: RunContext[AgentDeps]) -> str:
    repo = ctx.deps.repo
    if repo is None:
        return ""
    return f"\nThis channel is the **{repo.name}** product (GitHub: {repo.full_name})."


portfolio_agent = Agent(
    get_model(),
    deps_type=AgentDeps,
    system_prompt=PORTFOLIO_SYSTEM_PROMPT,
    tools=PORTFOLIO_TOOLS + CHANNEL_TOOLS,
)
