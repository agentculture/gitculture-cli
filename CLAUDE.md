# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace layout assumption

Path references in this file assume `ghafi` is checked out **alongside** its sibling AgentCulture projects in the same parent directory — i.e. `<workspace>/ghafi/`, `<workspace>/afi-cli/`, `<workspace>/cfafi/`, `<workspace>/steward/`. If your checkout layout differs, treat sibling paths as descriptive (they name the project, not a guaranteed filesystem location).

## What this project is

`ghafi` is the GitHub Agent First Interface — an AgentCulture manager that bootstraps and maintains sibling repositories on GitHub. It is the GitHub-side companion to `afi-cli` (the agent-first CLI scaffolder), `cfafi` (the CloudFlare-side manager), and `steward` (the alignment authority and skills supplier).

`ghafi` v0.x focuses on **bootstrapping new aligned siblings**: create the GitHub repository, scaffold the afi-cli python-cli template, and create the `pypi` / `testpypi` GitHub Environments needed for Trusted Publishing. Future versions will grow PR / issue / label / workflow / release verbs.

## Project shape

Distributed as **`ghafi-cli`** on PyPI (Trusted Publishing). The Python package is `ghafi`; the binary is `ghafi`. Layout follows the afi-cli pattern (top-level package, no `src/`):

```text
ghafi/                       # Python package (pip install ghafi-cli)
├── __init__.py              # __version__ via importlib.metadata("ghafi-cli")
├── __main__.py              # python -m ghafi
├── _api.py                  # urllib-only GitHub REST client
├── _env.py                  # GITHUB_TOKEN → GH_TOKEN resolution
├── cli/
│   ├── __init__.py          # argparse main(); _GhafiArgumentParser; _dispatch
│   ├── _errors.py           # GhafiError + EXIT_USER/ENV/AUTH/API codes
│   ├── _output.py           # emit_result / emit_error / emit_kv / emit_json
│   └── _commands/
│       ├── learn.py         # ghafi learn (and --json)
│       ├── explain.py       # ghafi explain <path>
│       ├── whoami.py        # GET /user
│       └── repo.py          # repo create / scaffold / env (sub-subparsers)
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
- **Run CLI from source:** `uv run ghafi --version`, `uv run ghafi learn`, `uv run python -m ghafi whoami`.
- **Tests:** `uv run pytest -n auto -v`. CI runs on every PR + push to main; coverage gate is 60%.
- **Lint:** `uv run black --check ghafi tests`, `uv run isort --check-only ghafi tests`, `uv run flake8 ghafi tests`, `uv run bandit -c pyproject.toml -r ghafi`, `markdownlint-cli2 "**/*.md"`, `bash .claude/skills/pr-review/scripts/portability-lint.sh`.
- **Version bump:** `python3 .claude/skills/version-bump/scripts/bump.py {patch|minor|major}` — updates `pyproject.toml` and prepends a CHANGELOG entry. **Required on every PR** (the `version-check` CI job comments and fails when the PR version equals main's).
- **Publish:** push to `main` triggers `.github/workflows/publish.yml` → `uv build` → publishes `ghafi-cli` to PyPI via Trusted Publishing (no API tokens). PRs publish a `.dev<run_number>` to TestPyPI for smoke-testing. Fork PRs are skipped (no OIDC context).

## GitHub authentication

`ghafi` reads the token from `GITHUB_TOKEN` first, falling back to `GH_TOKEN`. There is **no `gh` CLI fallback in the Python layer** — `ghafi` is stdlib-only (zero runtime deps) and uses `urllib` directly. If both env vars are unset, every GitHub-touching verb exits `2` with a remediation hint pointing at this file.

Required scopes:

- `repo` — create user-owned repositories.
- `admin:repo_hook` — manage Actions permissions and Environments.
- `admin:org` — additional, only when creating org-owned repositories.

## Mutation safety contract

Every verb that writes to GitHub **defaults to dry-run**. Pass `--apply` to commit. In dry-run, `ghafi` prints the JSON body it would POST/PUT and exits 0. This is enforced in code review (no automated check yet — flag it manually for any new mutating verb). Rationale: agents call `ghafi` in loops; safe defaults are the difference between a useful tool and a foot-gun.

## Trusted Publishing

`ghafi repo env` creates the GitHub-side Environment only. The PyPI side — registering the trusted publisher on pypi.org / test.pypi.org — is a one-time web flow per project; see <https://docs.pypi.org/trusted-publishers/>. Environments created by `ghafi repo env` store no secrets and configure no reviewers, since OIDC carries the auth.

## Conventions in use

- **Packaging:** `uv` + `pyproject.toml` (hatchling backend), `[project.scripts]` entry point.
- **Tests:** `pytest` (xdist + cov-xml in CI). Tests live under `tests/`. Network is mocked at the `ghafi._api.http_request` boundary; `subprocess.run` is mocked for `repo scaffold` tests.
- **Lint:** `flake8`, `bandit`, `black`, `isort`, `markdownlint-cli2`, plus a portability lint that catches absolute home-directory paths and tilde-prefixed dotfile references in committed docs/configs (see `.claude/skills/pr-review/scripts/portability-lint.sh`).
- **Versioning:** single source of truth in `pyproject.toml`. `ghafi.__version__` is read at import time from package metadata — there is no separate `__version__` literal.
- **Markdown:** repo-local `.markdownlint-cli2.yaml`. Don't depend on a per-user home-directory config — that's the precise portability failure the skills convention is designed to prevent.

## Skills convention

Every skill in `.claude/skills/<name>/` ships:

1. `SKILL.md` — explains *why* and *when* to use it. Frontmatter + short prose; no inline 10-step walk-throughs.
2. `scripts/<entry-point>.sh` (or `.py`) — the script that automates the workflow. Following the skill should be "run this script," not "do these ten manual steps."
3. **No external path dependencies.** Scripts must not reach into another skill's home-directory copy or any location outside this repo. If a skill needs functionality from elsewhere, vendor it into the skill's own `scripts/` directory. This makes skills portable across AgentCulture projects.

Per-machine paths live in **`.claude/skills.local.yaml`** (git-ignored). A committed `.claude/skills.local.yaml.example` documents every key.

`ghafi` currently vendors two skills:

- `version-bump/` (from `steward`) — semver bump + CHANGELOG prepend.
- `pr-review/` (from `steward`, narrowed) — portability lint and PR workflow guidance.

## Working with the AgentCulture mesh

`ghafi` is meant to be invoked **by other agents** (e.g., a `steward align` flow that creates the next sibling). Useful entry points:

- `afi-cli` — provides the `afi cli cite` command that `ghafi repo scaffold` shells out to. Sibling-relative path: `../afi-cli`.
- `cfafi` — reference implementation of the same agent-first pattern applied to CloudFlare. Sibling-relative path: `../cfafi`.
- `steward` — alignment authority; the original audit at `docs/steward/suggestions.md` drove v0.0.1. Sibling-relative path: `../steward`.

If `ghafi` grows verbs that overlap with `gh` (the GitHub CLI), favour the same flag/output shapes when reasonable, but don't take a runtime dep on `gh` — agents need `ghafi` to be self-contained.
