"""GitHub authentication strategy.

Two modes, chosen by which env vars are present:

1. GitHub App (recommended for production) — ONE app installed on your account
   and granted access to ONLY the four repos. Least privilege; the token is
   minted per-installation and auto-rotated by PyGithub. Set:
       GITHUB_APP_ID
       GITHUB_APP_INSTALLATION_ID
       GITHUB_APP_PRIVATE_KEY        (the full PEM, newlines and all)

2. Fine-grained PAT (fast to start) — a single fine-grained personal access
   token scoped to the four repos with Issues: Read+Write, Contents: Read,
   Metadata: Read. Set:
       GITHUB_TOKEN

App permissions to grant either way (nothing more — this IS the security ceiling):
    Issues: Read and write     (proposals, comments, labels)
    Contents: Read-only        (project.md, docs/releases/*)
    Metadata: Read-only        (always required)
There is deliberately no Pull requests/Administration/Workflows access, so the
app cannot merge, tag, deploy, or change branch protection — by construction,
not by trust.
"""

from __future__ import annotations

import os
from functools import lru_cache

from github import Auth, Github


@lru_cache(maxsize=1)
def get_github() -> Github:
    """Return a single, cached, authenticated PyGithub client."""
    app_id = os.environ.get("GITHUB_APP_ID")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")

    if app_id and installation_id and private_key:
        # Normalise an escaped PEM (e.g. when stored as a single-line secret).
        private_key = private_key.replace("\\n", "\n")
        auth = Auth.AppInstallationAuth(
            Auth.AppAuth(int(app_id), private_key),
            int(installation_id),
        )
        return Github(auth=auth)

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return Github(auth=Auth.Token(token))

    raise RuntimeError(
        "No GitHub credentials configured. Set the GITHUB_APP_* trio "
        "(recommended) or GITHUB_TOKEN (a fine-grained PAT)."
    )
