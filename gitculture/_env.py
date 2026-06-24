"""Environment-variable access — the sole credential ingress for gitculture.

Tokens are looked up in order: ``GITHUB_TOKEN`` then ``GH_TOKEN``. The
installed CLI never reads ``.env`` or config files.
"""

from __future__ import annotations

import os

from gitculture.cli._errors import EXIT_ENV_ERROR, GitcultureError

_TOKEN_ENV_NAMES = ("GITHUB_TOKEN", "GH_TOKEN")


def require_github_token() -> str:
    for name in _TOKEN_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    raise GitcultureError(
        code=EXIT_ENV_ERROR,
        message="no GitHub token in environment",
        remediation=(
            "export GITHUB_TOKEN=ghp_... (or GH_TOKEN) in your shell. "
            "The token needs `repo` scope to create repositories and "
            "`admin:repo_hook` to manage Actions permissions/environments."
        ),
    )
