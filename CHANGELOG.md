# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-24

### Added

- Dual PyPI publishing: the canonical distribution is now `gitculture-cli`; a thin `ghafi` compatibility shim depends on it so `pip install ghafi` keeps installing the tool. The GitHub repo remains `agentculture/ghafi` (unchanged deployment target).

### Changed

- Renamed the project to `gitculture-cli`; the primary command is now `gitculture`. The `ghafi` command remains as a backward-compatible alias (both entry points invoke the same CLI).
- Renamed the Python import package `ghafi` → `gitculture` (`python -m gitculture`). Internal `GhafiError` → `GitcultureError`, `_GhafiArgumentParser` → `_GitcultureArgumentParser`.

## [0.4.0] - 2026-06-24

### Added

- **Memory-discipline "Conventions and workflow" section in `CLAUDE.md`** — a
  per-task *recall-before / remember-after* convention (scope localized to this
  repo's nick) so the vendored `remember` / `recall` skills are actually used,
  not just present: `/recall` before non-trivial work to build on prior
  decisions instead of re-deriving them, and `/remember` when a non-obvious
  decision, constraint, fix-and-why, or hard-won gotcha surfaces. The section
  documents this repo's memory as **in-repo and public** — records resolve to
  `<repo-root>/.eidetic/memory` (committed, team- and mesh-shared). Inserted
  idempotently (skipped if already present), slotted under an existing
  "Conventions and workflow" heading when one exists, else appended.

### Changed

- **Refreshed the `remember` + `recall` wrappers from eidetic-cli 0.10.0**
  (cite-don't-import) — picks up eidetic's **project-local store default**: the
  files backend now resolves per record by visibility — PUBLIC records inside a
  git repo go to `<repo-root>/.eidetic/memory` (committed, team-shared), PRIVATE
  records (or any record outside a repo) go to `$HOME/.eidetic/memory` (never
  committed), an explicit `EIDETIC_DATA_DIR` still wins, and recall reads both
  stores and merges. Also carries the 0.9.3 hardening (interactive-stdin guard,
  `help` as a search term, SIGPIPE-safe suffix parsing). **Recipe policy
  override (the wrappers here are NOT byte-verbatim):** the injected default
  visibility is flipped from eidetic's `private` to **`public`**, so a plain
  `/remember` lands the note in `./.eidetic/memory` in this repo, kept as part
  of the repo — pass `--visibility private` to route a record to `$HOME`
  instead. `remember` drives `eidetic remember` (idempotent upsert of one JSON
  record or an NDJSON batch on stdin); `recall` drives `eidetic recall` with
  four search modes (exact / approximate / keyword / hybrid). Each `SKILL.md` is
  localized only in the illustrative `--scope <nick>` examples (Provenance keeps
  "First-party to eidetic-cli"). Runtime dep: the `eidetic` CLI on PATH (else a
  local eidetic-cli checkout with `uv`) — **`eidetic >= 0.10.0`** for the
  in-repo routing; on an older CLI the public records still work but are stored
  in `$HOME/.eidetic/memory` instead of in-repo. Propagated by rollout-cli's
  `eidetic-memory` recipe.

## [0.3.0] - 2026-06-23

### Added

- `ghafi pr list <org>` — read-only PR discovery. Scans the whole org via the GitHub Search API (`/search/issues`, paginated to the 1000-result cap) or one `--repo` via `/repos/{owner}/{repo}/pulls`, then re-checks each title client-side with `--match exact|prefix|substring` (case-insensitive) to kill the Search API's fuzzy false positives. `--state open|closed|all`, `--json` envelope.
- `ghafi pr approve <owner>/<repo> <number>` — submit an approving review (POST `/repos/{owner}/{repo}/pulls/{number}/reviews`, `event=APPROVE`). Dry-run by default; `--apply` commits. Accepts `owner/repo` or a bare name with `--owner`. Self-authored PRs (HTTP 422) map to a clear "your own pull request" error so batch callers can skip and continue.
- `ghafi pr merge <owner>/<repo> <number>` — merge via the direct merge endpoint (PUT `/repos/{owner}/{repo}/pulls/{number}/merge`), `--method squash|merge|rebase` (default squash), optional `--commit-title`/`--commit-message`. Dry-run by default; `--apply` commits. Same path as `gh pr merge --admin`: clears **non-required** failing checks (e.g. a non-blocking `lint`); a *required*-check / admin-locked branch-protection block maps to a clear "not mergeable" error (HTTP 405).
- mass-approve-prs skill (`.claude/skills/mass-approve-prs/`) — composes `pr list` + `pr approve` to approve every open PR in an org matching a title heading, in one dry-run-then-apply pass; tallies approved / skipped (self-authored) / failed.
- mass-merge-prs skill (`.claude/skills/mass-merge-prs/`) — composes `pr list` + `pr merge` to bulk-merge (default squash) every open PR matching a title heading; same dry-run-then-apply gate, tallies merged / skipped / failed.

### Changed

- `tests/test_mutation_safety.py` `MUTATING_VERBS` now includes `pr approve` and `pr merge`, each with a dry-run-no-write behavioral test.
- CLAUDE.md: documented the `pr` verbs + mass approve/merge flows, the project-shape tree, and the `repo`-scope coverage for PR review/merge/read (fine-grained: "Pull requests: write", "Contents: write" for merge, "Pull requests: read").
- Relocated the eidetic memory store from the eidetic CLI's home-directory default to a repo-local `./.eidetic` (git-ignored). The `remember`/`recall` wrappers now default `EIDETIC_DATA_DIR` to `<main-worktree>/.eidetic`, rooted at git's common dir so linked worktrees (the colleague backend) still share one store — preserving cross-agent recall while keeping memory inside the repo and out of committed home-directory paths. (This diverges the wrappers from their byte-verbatim eidetic-cli origin by one defaulted env var.)

### Fixed

- (Qodo review) `pr merge` now treats a `merged != true` response body as a failure (exit 4 with the API `message`) instead of reporting a phantom success — so `mass-merge-prs` can't over-count.
- (Qodo review) `pr list` now escapes embedded `"`/`\` in `--title` before building the `in:title "…"` Search-API qualifier, preventing malformed or injected queries.
- (Qodo review) `pr approve` / `pr merge` now reject a malformed `owner/repo` (empty owner or repo, or more than one `/`) with a clear user error instead of building an invalid API path.

## [0.2.0] - 2026-06-23

### Added

- **Vendored the `remember` + `recall` memory skills from eidetic-cli**
  (cite-don't-import) — the write/read halves of eidetic's shared memory
  surface, so this agent (Claude and its colleague backend)
  can persist facts across sessions and recall them later, sharing one store.
  `remember` drives `eidetic remember` (idempotent upsert of one JSON record or
  an NDJSON batch on stdin, dedup by id + content hash); `recall` drives
  `eidetic recall` with four search modes — exact / approximate / keyword /
  hybrid — each hit carrying text, full provenance metadata, a relevance score,
  and a freshness signal. The `.sh` wrappers are byte-verbatim from eidetic-cli
  (their first-party origin); each `SKILL.md` is localized only in the
  illustrative `--scope <nick>` examples (Provenance keeps "First-party to
  eidetic-cli"). Both default to this agent's PRIVATE scope, reading the suffix
  from `culture.yaml`. Runtime dep: the `eidetic` CLI on PATH (else a local
  eidetic-cli checkout with `uv`). Propagated by rollout-cli's `eidetic-memory`
  recipe.

## [0.1.0] - 2026-06-19

### Added

- `ghafi overview <org>` — org GitHub Actions minute-quota usage breakdown. Joins the enhanced-billing usage report against repo privacy and weights by runner-OS multiplier (Linux ×1, Windows ×2, macOS ×10); only private repos count against the quota. `--repo NAME` drills into one repo's workflow-run counts by trigger event. Read-only (no --apply). Needs the `admin:org` scope.
- actions-usage skill (`.claude/skills/actions-usage/`) — shell/gh/jq companion to `ghafi overview` for the same audit

## [0.0.2] - 2026-04-27

### Added

- doc/test alignment skill (`.claude/skills/doc-test-align/`) — drift detector for CLAUDE.md endpoint and verb claims
- bootstrap-sibling skill (`.claude/skills/bootstrap-sibling/`) — chains the four-step sibling bootstrap with dry-run-then-apply gates
- mutation-safety pytest module — asserts every mutating verb has --apply defaulting to False and performs no writes in dry-run
- Bootstrap walkthrough section in CLAUDE.md covering the four-step path from no-repo to Trusted-Publishing-ready

### Changed

- CLAUDE.md GitHub authentication: `repo` scope is sufficient for Environments (per GitHub REST docs); `admin:repo_hook` is no longer claimed required for v0.x verbs
- CLAUDE.md GitHub authentication: documented `GITHUB_TOKEN=$(gh auth token)` bridge for users with gh authenticated but no PAT exported

### Fixed

- Empirically incorrect scope claim for `ghafi repo env` — verified against agentculture/irc-lens bootstrap

## [0.0.1] - 2026-04-26

### Added

- `pyproject.toml` (`ghafi`, hatchling, zero runtime deps, Python ≥3.12).
- `ghafi/` package with `__main__.py` and version read from package metadata.
- `ghafi/cli/` afi-cli-shaped scaffold: `_GhafiArgumentParser`, `_dispatch`,
  `GhafiError` with five-code policy (success / user / env / auth / API),
  stdout-stderr split helpers in `_output.py`.
- `ghafi/_api.py` stdlib-only HTTP client for `https://api.github.com`,
  resolving the token from `GITHUB_TOKEN` then `GH_TOKEN` and mapping 401/403
  to exit 3 and other non-2xx to exit 4.
- `ghafi learn`, `ghafi explain`, `ghafi whoami` (agent-first contract).
- `ghafi repo create <name> [--org] [--private] [--description] [--apply]`
  with workflow permissions enabled after creation and 422-already-exists
  idempotency.
- `ghafi repo scaffold <path> [--lang python] [--apply]` — shells out to the
  `afi` binary; missing-binary exits 2 with remediation.
- `ghafi repo env <repo> [--owner] [--name pypi|testpypi] [--branch]
  [--apply]` — Trusted-Publishing GitHub Environment, no secrets, optional
  branch policy.
- `tests/` — 43 tests covering errors, output, learn, explain, whoami, all
  three repo verbs, and top-level dispatch.
- `.github/workflows/tests.yml` — pytest + black + isort + flake8 + bandit +
  markdownlint-cli2 + portability-lint, plus PR-only version-check job.
- `.github/workflows/publish.yml` — Trusted Publishing to PyPI on push to
  main; TestPyPI `.dev<run_number>` on PRs from non-fork branches.
- `.claude/skills/version-bump/` (vendored from steward) and
  `.claude/skills/pr-review/` (vendored from steward, narrowed to ghafi's
  reviewers).
- `.claude/skills.local.yaml.example` documenting per-machine config.
- `.flake8` and `.markdownlint-cli2.yaml` mirroring the steward / cfafi /
  afi-cli preset.
- `CLAUDE.md` rewritten with real install/run/test/lint commands, the
  GitHub-auth strategy, the dry-run-by-default contract, and the Skills
  convention.

### Notes

- Initial release. All ten alignment items from `docs/steward/suggestions.md`
  land here, plus the three GitHub-bootstrap verbs that motivated the work.
- The PyPI/TestPyPI side of Trusted Publishing (registering the trusted
  publisher) is a one-time web flow per project — see
  <https://docs.pypi.org/trusted-publishers/>.
