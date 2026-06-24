"""``gitculture learn`` — the learnability affordance.

Prints a structured self-teaching prompt with enough shape that an agent can
author its own usage skill without scraping ``--help``. Also supports
``--json`` for agents that would rather parse structure than text.
"""

from __future__ import annotations

import argparse

from gitculture import __version__
from gitculture.cli._output import emit_result

_TEXT = """\
gitculture — GitHub Agent First Interface (AgentCulture manager).

Purpose
-------
Bootstrap and manage AgentCulture sibling repositories on GitHub: create
new repos with sensible workflow permissions, scaffold the afi-cli
python-cli template into them, and create the `pypi` / `testpypi`
GitHub Environments needed for Trusted Publishing.

Commands
--------
  gitculture learn                Print this self-teaching prompt. Supports --json.
  gitculture explain <path>...    Print markdown docs for any noun/verb path.
                             Supports --json.
  gitculture whoami               Verify the configured GITHUB_TOKEN.
                             Supports --json.
  gitculture repo create <name>   Create a new GitHub repository (under the
                             authenticated user, or --org <org>). Dry-run
                             by default; --apply commits.
  gitculture repo scaffold <path> Render the afi-cli python-cli template into
                             <path> by shelling out to the `afi` binary.
                             Dry-run by default; --apply commits.
  gitculture repo env <repo>      Create a GitHub Environment (default name:
                             pypi) wired for Trusted Publishing — no
                             secrets stored. Repeat with --name testpypi
                             for the test environment. Dry-run by
                             default; --apply commits.
  gitculture overview <org>       Org Actions minute-quota usage (read-only).
                             Supports --json.
  gitculture pr list <org>        Find/search PRs in an org (read-only); filter
                             by --title / --repo / --state. Supports --json.
  gitculture pr approve <repo> <n> Approve a pull request. Dry-run by default;
                             --apply submits the review.
  gitculture pr merge <repo> <n>  Merge a pull request (squash by default) via
                             the direct merge endpoint — clears non-required
                             failing checks (e.g. lint). Dry-run by default;
                             --apply commits.

Mutation safety
---------------
Every verb that writes to GitHub defaults to dry-run. Pass --apply to
commit. In dry-run, gitculture prints the JSON body it would POST/PUT.

Authentication
--------------
The GitHub token is read from $GITHUB_TOKEN, falling back to $GH_TOKEN.
Required scopes: `repo` (create repos), `admin:repo_hook` (manage
environments and Actions permissions). For org repos, the token must
also have `admin:org`.

Trusted Publishing (PyPI/TestPyPI)
----------------------------------
`gitculture repo env` creates the GitHub-side Environment only. The PyPI
side — registering the trusted publisher on pypi.org / test.pypi.org —
is a one-time web flow per project. See:
  https://docs.pypi.org/trusted-publishers/

Machine-readable output
-----------------------
Every command supports --json. Errors in JSON mode emit
{"code", "message", "remediation"} to stderr. Stdout and stderr are
never mixed.

Exit-code policy
----------------
  0 success
  1 user-input error (bad flag, missing required arg)
  2 environment / setup error (no GITHUB_TOKEN; afi binary not on PATH)
  3 authentication error (401/403 from GitHub)
  4 upstream API error (4xx/5xx from GitHub, or non-zero exit from afi)

More detail
-----------
  gitculture explain gitculture
  gitculture explain repo
  gitculture explain repo create
  gitculture explain repo scaffold
  gitculture explain repo env
  gitculture explain overview
  gitculture explain pr approve

Homepage: https://github.com/agentculture/ghafi
"""


def _as_json_payload() -> dict[str, object]:
    return {
        "tool": "gitculture",
        "version": __version__,
        "purpose": (
            "Bootstrap and manage AgentCulture sibling repositories on GitHub: "
            "repo creation with workflow permissions, afi-cli scaffolding, and "
            "Trusted-Publishing environments."
        ),
        "commands": [
            {"path": ["learn"], "summary": "Self-teaching prompt."},
            {"path": ["explain"], "summary": "Markdown docs by noun/verb path."},
            {"path": ["whoami"], "summary": "Verify GITHUB_TOKEN against GET /user."},
            {
                "path": ["repo", "create"],
                "summary": "Create a GitHub repo (dry-run by default; --apply commits).",
            },
            {
                "path": ["repo", "scaffold"],
                "summary": "Shell out to `afi cli cite` to drop the python-cli template.",
            },
            {
                "path": ["repo", "env"],
                "summary": "Create a Trusted-Publishing environment (pypi or testpypi).",
            },
            {
                "path": ["overview"],
                "summary": "Org GitHub Actions minute-quota usage (read-only).",
            },
            {
                "path": ["pr", "list"],
                "summary": "Find/search PRs in an org (read-only); filter by title/repo/state.",
            },
            {
                "path": ["pr", "approve"],
                "summary": "Approve a PR (dry-run by default; --apply submits the review).",
            },
            {
                "path": ["pr", "merge"],
                "summary": "Merge a PR, squash by default (dry-run by default; --apply commits).",
            },
        ],
        "exit_codes": {
            "0": "success",
            "1": "user-input error",
            "2": "environment/setup error",
            "3": "authentication error",
            "4": "upstream API error",
        },
        "auth": {
            "env_vars": ["GITHUB_TOKEN", "GH_TOKEN"],
            "required_scopes": ["repo", "admin:repo_hook"],
            "org_extra_scopes": ["admin:org"],
        },
        "trusted_publishing_docs": "https://docs.pypi.org/trusted-publishers/",
        "json_support": True,
        "explain_pointer": "gitculture explain <path> (e.g. 'gitculture explain repo create')",
    }


def cmd_learn(args: argparse.Namespace) -> int:
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(_as_json_payload(), json_mode=True)
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "learn",
        help="Print a structured self-teaching prompt for agent consumers.",
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
