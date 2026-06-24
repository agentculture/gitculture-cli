# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace layout assumption

Path references in this file assume `gitculture-cli` is checked out **alongside** its sibling AgentCulture projects in the same parent directory — i.e. `<workspace>/gitculture-cli/`, `<workspace>/afi-cli/`, `<workspace>/cfafi/`, `<workspace>/steward/`. If your checkout layout differs, treat sibling paths as descriptive (they name the project, not a guaranteed filesystem location).

The installed CLI is **`gitculture`** (package `gitculture-cli`); the old `ghafi` command is a backward-compatible alias.

## What this project is

`gitculture` (formerly `ghafi`) is the GitHub Agent First Interface — an AgentCulture manager that bootstraps and maintains sibling repositories on GitHub. It is the GitHub-side companion to `afi-cli` (the agent-first CLI scaffolder), `cfafi` (the CloudFlare-side manager), and `steward` (the alignment authority and skills supplier).

`gitculture` v0.x focuses on **bootstrapping new aligned siblings**: create the GitHub repository, scaffold the afi-cli python-cli template, and create the `pypi` / `testpypi` GitHub Environments needed for Trusted Publishing. It also carries read/maintenance verbs — `overview` (org Actions-minute usage) and `pr` (find and approve pull requests across the org). Future versions will grow issue / label / workflow / release verbs.

## Project shape

Distributed as **`gitculture-cli`** on PyPI (Trusted Publishing); installs the `gitculture` binary plus a backward-compatible `ghafi` alias. The same code is **also** published under the legacy PyPI name **`ghafi`** so `pip install ghafi` keeps installing the tool — that is a full, zero-dependency distribution built from this repo by overriding `[project].name` at publish time (not a shim/metapackage; see `.github/workflows/publish.yml`). Layout follows the afi-cli pattern (top-level package, no `src/`):

```text
gitculture/                  # Python package (pip install gitculture-cli)
├── __init__.py              # __version__ via importlib.metadata("gitculture-cli")
├── __main__.py              # python -m gitculture
├── _api.py                  # urllib-only GitHub REST client
├── _env.py                  # GITHUB_TOKEN → GH_TOKEN resolution
├── cli/
│   ├── __init__.py          # argparse main(); _GitcultureArgumentParser; _dispatch
│   ├── _errors.py           # GitcultureError + EXIT_USER/ENV/AUTH/API codes
│   ├── _output.py           # emit_result / emit_error / emit_kv / emit_json
│   └── _commands/
│       ├── learn.py         # gitculture learn (and --json)
│       ├── explain.py       # gitculture explain <path>
│       ├── whoami.py        # GET /user
│       ├── repo.py          # repo create / scaffold / env (sub-subparsers)
│       ├── overview.py      # org Actions minute-quota usage (read-only)
│       └── pr.py            # pr list (read-only) / pr approve / pr merge (sub-subparsers)
└── explain/
    ├── __init__.py          # resolve(path) → markdown
    └── catalog.py           # ENTRIES (path-tuple → markdown)
tests/                       # pytest suite, urllib + subprocess stubs
.claude/skills/              # see "Skills convention" below
.github/workflows/           # tests.yml + publish.yml (OIDC Trusted Publishing)
docs/steward/suggestions.md  # original audit driving v0.0.1
pyproject.toml               # version source-of-truth
CHANGELOG.md                 # Keep-a-Changelog
```

## Build / test / publish

- **Install for dev:** `uv sync`.
- **Run CLI from source:** `uv run gitculture --version`, `uv run gitculture learn`, `uv run python -m gitculture whoami`, `uv run gitculture overview agentculture`, `uv run gitculture pr list agentculture --title "<heading>"`.
- **Tests:** `uv run pytest -n auto -v`. CI runs on every PR + push to main; coverage gate is 60%.
- **Lint:** `uv run black --check gitculture tests`, `uv run isort --check-only gitculture tests`, `uv run flake8 gitculture tests`, `uv run bandit -c pyproject.toml -r gitculture`, `markdownlint-cli2 "**/*.md"`, `bash .claude/skills/pr-review/scripts/portability-lint.sh`.
- **Version bump:** `python3 .claude/skills/version-bump/scripts/bump.py {patch|minor|major}` — updates `pyproject.toml` and prepends a CHANGELOG entry. **Required on every PR** (the `version-check` CI job comments and fails when the PR version equals main's).
- **Publish:** push to `main` triggers `.github/workflows/publish.yml` → `uv build` (twice, once per distribution name) → publishes **both** `gitculture-cli` and the legacy `ghafi` name to PyPI via Trusted Publishing (no API tokens). PRs publish a `.dev<run_number>` of both to TestPyPI for smoke-testing. Fork PRs are skipped (no OIDC context).

## GitHub authentication

`gitculture` reads the token from `GITHUB_TOKEN` first, falling back to `GH_TOKEN`. There is **no `gh` CLI fallback in the Python layer** — `gitculture` is stdlib-only (zero runtime deps) and uses `urllib` directly. If both env vars are unset, every GitHub-touching verb exits `2` with a remediation hint pointing at this file.

If you have `gh` authenticated but no PAT exported, bridge it for one command: `GITHUB_TOKEN=$(gh auth token) gitculture <verb> …`. Or export it for the shell: `export GITHUB_TOKEN=$(gh auth token)`. This keeps gitculture stdlib-only while leveraging your existing `gh` session.

Required scopes (verified against the v0.x verb set):

- `repo` — create user-owned repositories, manage Environments (PUT `/repos/{owner}/{repo}/environments/{name}`), write Actions repository permissions (PUT `/repos/{owner}/{repo}/actions/permissions`, used by `repo create` to enable workflows), submit PR reviews (`gitculture pr approve` → POST `/repos/{owner}/{repo}/pulls/{number}/reviews`), and merge PRs (`gitculture pr merge` → PUT `/repos/{owner}/{repo}/pulls/{number}/merge`). It also covers the read side of `gitculture pr list` against private repos (`/search/issues` and `/repos/{owner}/{repo}/pulls`); a fine-grained token needs "Pull requests: write" for `pr approve`, "Contents: write" + "Pull requests: write" for `pr merge`, and "Pull requests: read" for `pr list`. All accept classic-PAT `repo` per GitHub REST docs; this is what `gh auth login` gives you by default. Forcing a merge past a *required* failing check additionally needs admin rights on the repo (and branch protection that doesn't lock out administrators).
- `admin:org` — required by **two** surfaces: (1) creating **org-owned** repositories (org membership with create-repo permission is the actual gate; the scope is required for some org configurations), and (2) `gitculture overview`, which reads the enhanced-billing usage report (GET `/organizations/{org}/settings/billing/usage`) — `read:org` alone returns 403 there, and the legacy `/settings/billing/actions` endpoint was retired (HTTP 410). `overview` also reads `/orgs/{org}/repos` (privacy join) and, with `--repo`, `/repos/{owner}/{repo}/actions/runs` — both covered by `repo`.
- `admin:repo_hook` — **not currently needed** by any v0.x verb. Would be required only if gitculture grew verbs that manage repository webhooks; the existing Environments and Actions-permissions endpoints both accept `repo` alone.

## Mutation safety contract

Every verb that writes to GitHub **defaults to dry-run**. Pass `--apply` to commit. In dry-run, `gitculture` prints the JSON body it would POST/PUT and exits 0. This is enforced both in code review and by `tests/test_mutation_safety.py`, which walks the argparse tree to assert every mutating verb exposes `--apply` defaulting to False and performs no HTTP writes (or `subprocess.run` invocations) without it. Add new mutating verbs to that test's `MUTATING_VERBS` list. Rationale: agents call `gitculture` in loops; safe defaults are the difference between a useful tool and a foot-gun.

## Trusted Publishing

`gitculture repo env` creates the GitHub-side Environment only. The PyPI side — registering the trusted publisher on pypi.org / test.pypi.org — is a one-time web flow per project; see <https://docs.pypi.org/trusted-publishers/>. Environments created by `gitculture repo env` store no secrets and configure no reviewers, since OIDC carries the auth.

**This repo publishes the SAME code under TWO PyPI project names** (see "Project shape"): the canonical `gitculture-cli` and the legacy `ghafi`, both full zero-dependency distributions from `.github/workflows/publish.yml`. Trusted Publishing is keyed on the `(repository, workflow, environment)` triple — **not** on the artifact contents — so **each PyPI project needs its own trusted-publisher entry**, both pointing at repo `agentculture/gitculture-cli`, workflow `publish.yml`, environment `pypi` (and `testpypi` on test.pypi.org):

- `ghafi` — predates the rename; update its existing trusted-publisher entry so the repository is `agentculture/gitculture-cli` (the repo was renamed; GitHub's OIDC token now carries the new slug). It then keeps receiving the full `ghafi`-named build.
- `gitculture-cli` — register a (pending) publisher on both pypi.org and test.pypi.org, or the "Publish gitculture-cli" step fails. Register at <https://pypi.org/manage/account/publishing/> and <https://test.pypi.org/manage/account/publishing/> with owner `agentculture`, repo `gitculture-cli`, workflow `publish.yml`, environment `pypi` / `testpypi`.

## Bootstrap walkthrough (new sibling)

From "no repo" to "Trusted-Publishing-ready sibling" in four automated steps plus one manual web-flow step. Each `gitculture --apply` step prints the JSON body in dry-run first; review before adding the flag.

1. **Create on GitHub**

   ```bash
   gitculture repo create --org agentculture --description "<one-liner>" <name>           # dry-run
   gitculture repo create --org agentculture --description "<one-liner>" <name> --apply
   ```

2. **Clone locally as a sibling**

   ```bash
   git clone https://github.com/agentculture/<name>.git ../<name>
   ```

3. **Cite the afi-cli reference template** — note this **does not** instantiate a runnable project; it writes the template into `.afi/reference/python-cli/` (the cite-don't-import pattern). You instantiate `{{slug}}/` into the actual package separately.

   ```bash
   gitculture repo scaffold --apply ../<name>
   ```

4. **Create both Trusted Publishing environments**

   ```bash
   gitculture repo env --owner agentculture --name pypi --branch main --apply <name>
   gitculture repo env --owner agentculture --name testpypi --apply <name>
   ```

5. **Manual (one-time per project, web only):** register the trusted publisher on <https://pypi.org/manage/account/publishing/> and <https://test.pypi.org/manage/account/publishing/>, pointing at `agentculture/<name>`, workflow `publish.yml`, environment `pypi` (and `testpypi` on the test side).

A `.claude/skills/bootstrap-sibling/scripts/bootstrap.sh` helper drives the full flow with a confirmation gate: it dry-runs the GitHub mutations first, then on `--apply` runs `repo create`, performs the local `git clone`, runs `repo scaffold`, and creates the `pypi` and `testpypi` environments as separate calls.

## Pull-request verbs and mass actions

`gitculture pr list <org>` finds PRs org-wide (via the Search API) or in one `--repo`, filtered by `--title` with `--match exact|prefix|substring`. The two write verbs act on a single PR, dry-run by default:

- `gitculture pr approve <owner>/<repo> <number>` — submits an approving review. Self-authored PRs surface a clear "your own pull request" error (GitHub forbids self-approval) rather than crashing a batch.
- `gitculture pr merge <owner>/<repo> <number>` — merges via the **direct** merge endpoint (PUT `/repos/{owner}/{repo}/pulls/{number}/merge`), `--method squash|merge|rebase` (default squash). This is the same path as `gh pr merge --admin`: it merges past **non-required** failing checks (e.g. a failing `lint` that isn't a required status check — the "unstable" red-button state). It does **not** bypass *required* checks when branch protection includes administrators; that returns HTTP 405, surfaced as a clear "not mergeable" error.

These compose into mass actions: list the matches, eyeball them, then act on each. Two skills drive the full loop (`gitculture pr list … --json` to discover, then one write verb per match — dry-run by default, `--apply` to commit, tallying done / skipped / failed):

- `.claude/skills/mass-approve-prs/scripts/mass-approve-prs.sh` — bulk approve.
- `.claude/skills/mass-merge-prs/scripts/mass-merge-prs.sh` — bulk merge (`--method`, default squash); use to land a fleet of identical rollout PRs past non-blocking lint.

## Conventions in use

- **Packaging:** `uv` + `pyproject.toml` (hatchling backend), `[project.scripts]` entry point.
- **Tests:** `pytest` (xdist + cov-xml in CI). Tests live under `tests/`. Network is mocked at the `gitculture._api.http_request` boundary; `subprocess.run` is mocked for `repo scaffold` tests.
- **Lint:** `flake8`, `bandit`, `black`, `isort`, `markdownlint-cli2`, plus a portability lint that catches absolute home-directory paths and tilde-prefixed dotfile references in committed docs/configs (see `.claude/skills/pr-review/scripts/portability-lint.sh`).
- **Versioning:** single source of truth in `pyproject.toml`. `gitculture.__version__` is read at import time from package metadata — there is no separate `__version__` literal.
- **Markdown:** repo-local `.markdownlint-cli2.yaml`. Don't depend on a per-user home-directory config — that's the precise portability failure the skills convention is designed to prevent.

## Skills convention

Every skill in `.claude/skills/<name>/` ships:

1. `SKILL.md` — explains *why* and *when* to use it. Frontmatter + short prose; no inline 10-step walk-throughs.
2. `scripts/<entry-point>.sh` (or `.py`) — the script that automates the workflow. Following the skill should be "run this script," not "do these ten manual steps."
3. **No external path dependencies.** Scripts must not reach into another skill's home-directory copy or any location outside this repo. If a skill needs functionality from elsewhere, vendor it into the skill's own `scripts/` directory. This makes skills portable across AgentCulture projects.

Per-machine paths live in **`.claude/skills.local.yaml`** (git-ignored). A committed `.claude/skills.local.yaml.example` documents every key.

`gitculture` currently vendors two skills:

- `version-bump/` (from `steward`) — semver bump + CHANGELOG prepend.
- `pr-review/` (from `steward`, narrowed) — portability lint and PR workflow guidance.

## Working with the AgentCulture mesh

`gitculture` is meant to be invoked **by other agents** (e.g., a `steward align` flow that creates the next sibling). Useful entry points:

- `afi-cli` — provides the `afi cli cite` command that `gitculture repo scaffold` shells out to. Sibling-relative path: `../afi-cli`.
- `cfafi` — reference implementation of the same agent-first pattern applied to CloudFlare. Sibling-relative path: `../cfafi`.
- `steward` — alignment authority; the original audit at `docs/steward/suggestions.md` drove v0.0.1. Sibling-relative path: `../steward`.

If `gitculture` grows verbs that overlap with `gh` (the GitHub CLI), favour the same flag/output shapes when reasonable, but don't take a runtime dep on `gh` — agents need `gitculture` to be self-contained.

## Conventions and workflow

**Memory discipline — recall before, remember after.** This repo keeps its
eidetic memory **in-repo and public**: records resolve to
`<repo-root>/.eidetic/memory` — committed, and shared with the team and mesh
peers (the `claude` and `colleague` backends both read the same
`ghafi` scope — the eidetic scope name is kept as `ghafi` for memory
continuity across the rename; it is independent of the CLI/repo name and
is **not** renamed, so existing records stay addressable), so memory
travels with the repo, not a private home-dir store. Make it a per-task habit:

- **`/recall` before you start.** Search the store for the area you're about
  to touch — prior decisions, gotchas, "have we done this before?" — so you
  build on what's already known instead of re-deriving it. Do this before
  non-trivial tasks, not just when asked.
- **`/remember` when something worth keeping surfaces.** A non-obvious
  decision and its rationale, a constraint, a fix and *why* it was needed, a
  gotcha that cost time, a fact the next session would otherwise re-learn.
  Capture it as it happens, not at the end when it's faded.

A plain `/remember` lands the note in `./.eidetic/memory` in this repo — no
flag needed (the wrappers here default to `--visibility public`; in-repo
routing needs `eidetic >= 0.10.0`, older CLIs keep records in `$HOME`). Keep
something out of the committed store only by passing `--visibility private`
(routes to `$HOME/.eidetic/memory`, never committed); `/recall` reads both
stores and merges. Don't store what the repo already records (code structure,
git history, what's already in this file or `CHANGELOG.md`) — store what you'd
have to re-derive. These are the `recall`/`remember` skills (`.claude/skills/`),
backed by the `eidetic` store.
