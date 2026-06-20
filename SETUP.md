# Cofounder agent — setup

A per-project Slack agent that lets a non-technical cofounder see live project
status, get onboarded, and **map product phases/features in natural language**.
The agent reads everything from GitHub (the source of truth) and writes ideas
back as `proposal` issues into an **Intake queue** that you triage with Claude
Code. It cannot merge, tag, deploy, or change code — by construction.

These files are an **overlay** on the official Slack starter:
`slack-samples/bolt-python-starter-agent`, the **`pydantic-ai`** variant.

---

## 1. Fork and trim

1. Fork `slack-samples/bolt-python-starter-agent`.
2. The repo ships three variants. Keep only **`pydantic-ai/`** — move its contents
   to the repo root and delete `claude-agent-sdk/` and `openai-agents-sdk/`.
3. Copy this overlay over the root, replacing files where paths match.

## 2. Delete from the starter

- `agent/agent.py`  → replaced by `agent/agents.py` + `agent/runtime.py`.
- `agent/tools/emoji_reaction.py`  → the demo tool; gone.
- The **Slack MCP** wiring is dropped (the agent's only tools are GitHub). It's
  already absent from this overlay's `agent/` — just make sure no leftover
  imports of `emoji_reaction` or `MCPServerStreamableHTTP` remain.

Unchanged from the fork (keep as-is): `app.py`, `listeners/__init__.py`,
`thread_context/`, `app_home_opened`, `assistant_thread_started`, the feedback
buttons. The two listeners `app_mentioned.py` and `message.py` are replaced here.

## 3. GitHub access (the security ceiling)

**Recommended — one GitHub App scoped to your four repos:**
1. GitHub → Settings → Developer settings → GitHub Apps → New.
2. Permissions (nothing more): **Issues: Read and write**, **Contents:
   Read-only**, **Metadata: Read-only**. No Pull requests, Administration, or
   Workflows access — that's what makes "merge / tag / deploy" impossible.
3. Install it on your account and grant access to **only** sabevalor,
   spreadsheetmillionaire, cutecumber, pandavo.
4. Note the **App ID**, generate a **private key** (PEM), and grab the
   **Installation ID** (in the install's URL). Put them in env (step 7).

**Quickstart — a fine-grained PAT:** scope it to the four repos with Issues
Read+Write, Contents Read, Metadata Read; set `GITHUB_TOKEN`. Swap to the App for
production.

## 4. Slack app

1. Use the starter's `manifest.json` to create the app (Socket Mode is already
   enabled in it). Bot scopes you need: `app_mentions:read`, `chat:write`,
   `channels:history`, `groups:history`, `im:history`, `reactions:write`,
   `assistant:write`.
2. Generate an **app-level token** with `connections:write` → `SLACK_APP_TOKEN`.
   Copy the **Bot User OAuth Token** → `SLACK_BOT_TOKEN`.
3. Install to the workspace and **invite the bot to each project channel** and
   to `#portfolio`.

## 5. The Intake queue (the board view)

The agent auto-creates the labels (`proposal`, `type:phase`, `type:feature`) the
first time it files something. On each repo's Project board, add a view filtered
to **`label:proposal`**, grouped by the `type:` label — that's your Intake lane.
Proposals are unmilestoned on purpose; promoting one (assign a milestone, drop
`proposal`, move to Todo) is the deliberate act you do later with Claude Code.

## 6. Wire the channels

Edit `config/repos.py`:
- confirm the four repo slugs (fix `pandavo` if its repo name differs),
- replace each `C_..._REPLACE_ME` with the real Slack channel ID (channel → its
  name → About → Channel ID),
- set `PORTFOLIO_CHANNEL_ID`.

## 7. Run locally

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env      # fill it in
python app.py
```

In a wired channel: `@<bot> where do we stand?` → it reads live status. Then
`@<bot> I have an idea for a feature` → it should ask questions, reflect back,
and only then file a proposal. Check the issue appears with the right labels.

## 8. Deploy to Fly

```bash
fly launch --no-deploy          # accept/adjust fly.toml
fly secrets set \
  SLACK_BOT_TOKEN=... SLACK_APP_TOKEN=... ANTHROPIC_API_KEY=... \
  GITHUB_APP_ID=... GITHUB_APP_INSTALLATION_ID=... \
  GITHUB_APP_PRIVATE_KEY="$(cat your-app.private-key.pem)"
fly deploy
fly logs                        # confirm "connected" to Slack
```

(Keep the private key in Fly secrets only — never in the repo, never echoed to a
channel. Same hygiene as your `ANTHROPIC_API_KEY`-only-in-`avm/.env` rule.)

## 9. How it ties to your existing workflow

The Slack app and Claude Code never talk directly — **GitHub is the message bus.**
The cofounder shapes ideas in Slack → they land as `proposal` issues → in a
Claude Code session you run your triage ritual: list open proposals oldest-first
and promote / defer / reject each. Promoted `type:feature` → milestoned execution
issue inside your normal system; promoted `type:phase` → folded into `project.md`;
rejected → rationale to `DECISIONS.md`. Nothing speculative enters execution until
you decide. The boundary you already keep — tag = your "ship it" — is untouched.
```
