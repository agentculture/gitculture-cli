"""Markdown catalog for ``ghafi explain <path>``.

Each entry is verbatim markdown. Keys are command-path tuples. The empty
tuple and ``("ghafi",)`` both resolve to the root entry (aliased).
"""

from __future__ import annotations

_ROOT = """\
# ghafi

ghafi is the GitHub Agent First Interface — an AgentCulture manager for
bootstrapping and maintaining sibling repositories on GitHub.

## Verbs

- `ghafi learn` — structured self-teaching prompt.
- `ghafi explain <path>` — markdown docs for any noun/verb.
- `ghafi whoami` — verify the configured GitHub token.
- `ghafi repo create <name>` — create a new repository.
- `ghafi repo scaffold <path>` — drop the afi-cli python-cli template.
- `ghafi repo env <repo>` — create a Trusted-Publishing environment.
- `ghafi overview <org>` — org Actions minute-quota usage (read-only).
- `ghafi pr list <org>` — find/search PRs in an org (read-only).
- `ghafi pr approve <repo> <number>` — approve a PR.
- `ghafi pr merge <repo> <number>` — merge a PR (squash by default).

## Mutation safety

Every verb that writes to GitHub defaults to dry-run. Pass `--apply` to
commit. In dry-run, ghafi prints the JSON body it would send.

## Authentication

`GITHUB_TOKEN` (preferred) or `GH_TOKEN`. Required scopes: `repo`,
`admin:repo_hook`. For org repos: `admin:org`.

## Exit-code policy

- `0` success
- `1` user-input error
- `2` environment / setup error (no token; `afi` binary missing)
- `3` authentication error (401/403)
- `4` upstream API error (4xx/5xx from GitHub, non-zero exit from afi)

## See also

- `ghafi explain repo`
- `ghafi explain repo create`
- `ghafi explain repo scaffold`
- `ghafi explain repo env`
- `ghafi explain whoami`
- `ghafi explain overview`
- `ghafi explain pr`
- `ghafi explain pr list`
- `ghafi explain pr approve`
- `ghafi explain pr merge`
"""

_LEARN = """\
# ghafi learn

Prints a structured self-teaching prompt covering ghafi's purpose,
command map, exit-code policy, `--json` support, and `explain` pointer.

## Usage

    ghafi learn
    ghafi learn --json

In JSON mode, emits
`{"tool", "version", "purpose", "commands", "exit_codes", "auth",
"json_support", "explain_pointer"}` to stdout.
"""

_EXPLAIN = """\
# ghafi explain <path>

Prints markdown documentation for any noun/verb path.

## Usage

    ghafi explain ghafi
    ghafi explain repo
    ghafi explain repo create
    ghafi explain repo env --json

Unknown paths exit `1` with a `hint:` pointing at `ghafi explain ghafi`.
"""

_WHOAMI = """\
# ghafi whoami

Verifies the configured GitHub token by calling `GET /user`. Reports the
authenticated `login`, numeric `id`, and account `type` (User or
Organization).

## Usage

    ghafi whoami
    ghafi whoami --json

## Exit codes

- `0` success
- `2` no token in environment
- `3` 401/403 from GitHub (token invalid or missing scopes)
"""

_REPO = """\
# ghafi repo

The `repo` noun groups verbs that bootstrap a new AgentCulture sibling
repository:

- `ghafi repo create <name>` — create a GitHub repository under the
  authenticated user, or under `--org <org>`. Enables Actions and sets
  workflow permissions to `all`.
- `ghafi repo scaffold <path>` — shell out to `afi cli cite` to render
  the python-cli template into `<path>`.
- `ghafi repo env <repo>` — create a GitHub Environment named `pypi`
  (default) or `testpypi` (`--name testpypi`) for Trusted Publishing.

See `ghafi explain repo create`, `ghafi explain repo scaffold`, and
`ghafi explain repo env` for details.
"""

_REPO_CREATE = """\
# ghafi repo create <name> [--org ORG] [--private] [--description TEXT]
                          [--apply] [--json]

Create a new GitHub repository.

## What it does

1. POSTs to `/user/repos` (or `/orgs/{org}/repos` if `--org` is given)
   with body: `{name, private, description, auto_init, has_issues,
   has_wiki: false, has_projects: false}`.
2. After 201, PUTs `/repos/{owner}/{name}/actions/permissions` to set
   `enabled: true, allowed_actions: "all"`.
3. If GitHub returns 422 ("name already exists"), `repo create` re-GETs
   the existing repo and exits `0` with an "already exists" result —
   bootstrapping is re-runnable.

## Dry-run

Default. Prints the JSON body that *would* POST. Pass `--apply` to
actually create the repo.

## JSON shape

    {
      "success": bool,
      "dry_run": bool,
      "would_post" | "created": {...},
      "repo_url": "https://github.com/<owner>/<name>",
      "actions_permissions_set": bool
    }
"""

_REPO_SCAFFOLD = """\
# ghafi repo scaffold <path> [--lang python] [--apply] [--json]

Drop the afi-cli python-cli template into `<path>` by shelling out to
the `afi` binary.

## What it does

1. Resolves the `afi` binary on `$PATH`. If not found, exits `2` with a
   remediation pointing at `pip install afi-cli`.
2. With `--apply`: runs `afi cli cite <path> --lang <lang> --json`,
   parses the report, and re-emits it through ghafi's structured
   output.
3. Without `--apply`: describes the planned action *without* invoking
   `afi`. (The `afi` engine has no native dry-run — running it writes
   files unconditionally — so ghafi's dry-run is descriptive only.)

## Errors

- `afi` not on PATH → exit `2`.
- `afi` exits non-zero → exit `4`, with `afi`'s stderr in remediation.
"""

_REPO_ENV = """\
# ghafi repo env <repo> [--owner OWNER] [--name pypi|testpypi|<custom>]
                       [--branch PATTERN] [--apply] [--json]

Create or update a GitHub Environment for Trusted Publishing.

## What it does

1. Calls `PUT /repos/{owner}/{repo}/environments/{name}`.
2. Sets `deployment_branch_policy: {protected_branches: false,
   custom_branch_policies: true}` when `--branch` is given; otherwise
   `null` (any branch can deploy).
3. Stores no secrets and configures no reviewers — Trusted Publishing
   uses OIDC, so the `pypi`/`testpypi` environments need no credentials.

## Owner resolution

If `--owner` is omitted, ghafi calls `GET /user` to discover the
authenticated login and uses it as the owner.

## Both environments

Run the verb twice:

    ghafi repo env myproject --name pypi --apply
    ghafi repo env myproject --name testpypi --apply

## PyPI side (NOT automated)

The PyPI/TestPyPI side — registering the trusted publisher — is a
one-time web flow per project. See:
  https://docs.pypi.org/trusted-publishers/
"""


_OVERVIEW = """\
# ghafi overview <org> [--month YYYY-MM] [--repo NAME] [--json]

Read-only audit of an org's GitHub Actions minute-quota usage — answers
"why are we near our included-minutes limit".

## What it does

1. Lists `/orgs/{org}/repos` to learn which repos are private.
2. Reads the enhanced-billing usage report
   (`GET /organizations/{org}/settings/billing/usage?year=&month=`).
3. Keeps only the PRIVATE repos (public repos get unlimited free minutes
   and never touch the quota) and weights each by runner-OS multiplier:
   Linux ×1, Windows ×2, macOS ×10. A small macOS matrix leg can outrank
   a busy Linux repo — that is the signal to act on.

With `--repo NAME` it instead reads `/repos/{org}/{repo}/actions/runs`
and groups the most recent 100 runs by workflow + trigger event, plus the
month's total run count — to explain *why* one repo is heavy.

## Scope

Needs `admin:org` — the billing-usage endpoint returns 403 for `read:org`
alone, and the legacy `/settings/billing/actions` endpoint is retired
(HTTP 410). The repo + runs reads are covered by `repo`.

## JSON shape (org mode)

    {
      "org": str, "month": "YYYY-MM",
      "repos": [{"repo": str, "weighted": int, "raw": int}, ...],
      "private_total_weighted": int,
      "private_total_raw": int,
      "public_total_raw": int
    }
"""


_PR = """\
# ghafi pr

The `pr` noun groups pull-request verbs:

- `ghafi pr list <org>` — read-only. Find open (or closed/all) PRs in an
  org, optionally narrowed to one `--repo` and/or filtered by `--title`.
- `ghafi pr approve <repo> <number>` — submit an approving review. Dry-run
  by default; `--apply` commits.
- `ghafi pr merge <repo> <number>` — merge a PR (squash by default) via the
  direct merge endpoint. Dry-run by default; `--apply` commits.

Together they drive mass actions: `pr list` discovers matching PRs, you
review them, then `pr approve` / `pr merge` acts on each one. The write
verbs stay single-PR and dry-run-default so every mutation is reviewable.

See `ghafi explain pr list`, `ghafi explain pr approve`, and
`ghafi explain pr merge`.
"""

_PR_LIST = """\
# ghafi pr list <org> [--repo NAME] [--title TEXT]
                     [--match exact|prefix|substring] [--state open|closed|all]
                     [--json]

Find pull requests in an org. Read-only — never writes.

## What it does

- **Without `--repo`:** scans the whole org via the Search API
  (`GET /search/issues?q=org:<org> type:pr state:<state> in:title "<title>"`),
  paginating up to the Search API's 1000-result cap, and keeps only PRs.
- **With `--repo`:** lists that repo's pulls directly
  (`GET /repos/{org}/{repo}/pulls?state=<state>`, paginated).

## Title matching

`--title` filters client-side (the Search API's `in:title` is fuzzy
full-text, so results are re-checked exactly). All comparisons are
case-insensitive and whitespace-stripped:

- `exact` (default) — title equals the query.
- `prefix` — title starts with the query (heading semantics).
- `substring` — query appears anywhere in the title.

## JSON shape

    {
      "org": str, "repo": str|null, "state": str,
      "title": str|null, "match": str, "count": int,
      "pull_requests": [
        {"owner", "repo", "number", "title", "author", "url", "draft"}, ...
      ]
    }
"""

_PR_APPROVE = """\
# ghafi pr approve <repo> <number> [--owner OWNER] [--body TEXT]
                                  [--apply] [--json]

Submit an approving review for one pull request.

## What it does

POSTs `/repos/{owner}/{repo}/pulls/{number}/reviews` with
`{"event": "APPROVE", "body": <--body if given>}`.

`<repo>` may be `owner/repo` (the split wins) or a bare name with
`--owner`. There is no whoami fallback — an approval is always against a
specific upstream owner, so one must be given explicitly.

## Dry-run

Default. Prints the JSON body that *would* POST. Pass `--apply` to submit
the review.

## Self-approval

GitHub rejects approving your own PR (HTTP 422). `pr approve` maps that to
a clear error ("it is your own pull request") so a batch caller can skip
and continue.

## JSON shape

    {
      "success": bool, "dry_run": bool,
      "approved": "owner/repo#number",
      "review_id": int, "review_state": "APPROVED",
      "review_url": str
    }
"""


_PR_MERGE = """\
# ghafi pr merge <repo> <number> [--owner OWNER]
                               [--method squash|merge|rebase]
                               [--commit-title T] [--commit-message M]
                               [--apply] [--json]

Merge one pull request via the direct merge endpoint.

## What it does

PUTs `/repos/{owner}/{repo}/pulls/{number}/merge` with
`{"merge_method": <--method>}` (default `squash`), plus optional
`commit_title` / `commit_message` overrides.

This is the *direct* merge endpoint — the same path `gh pr merge --admin`
uses. It merges past **non-required** failing checks (e.g. a failing
`lint` that isn't a required status check, which shows in the UI as an
"unstable"/red merge button). It does **not** magically bypass *required*
checks when branch protection includes administrators — that returns HTTP
405 and is surfaced as a clear "not mergeable" error.

`<repo>` may be `owner/repo` or a bare name with `--owner`.

## Dry-run

Default. Prints the JSON body that *would* PUT. Pass `--apply` to merge.

## JSON shape

    {
      "success": bool, "dry_run": bool,
      "merged": bool, "pr": "owner/repo#number",
      "sha": str, "message": str
    }
"""


ENTRIES: dict[tuple[str, ...], str] = {
    (): _ROOT,
    ("ghafi",): _ROOT,
    ("learn",): _LEARN,
    ("explain",): _EXPLAIN,
    ("whoami",): _WHOAMI,
    ("repo",): _REPO,
    ("repo", "create"): _REPO_CREATE,
    ("repo", "scaffold"): _REPO_SCAFFOLD,
    ("repo", "env"): _REPO_ENV,
    ("overview",): _OVERVIEW,
    ("pr",): _PR,
    ("pr", "list"): _PR_LIST,
    ("pr", "approve"): _PR_APPROVE,
    ("pr", "merge"): _PR_MERGE,
}
