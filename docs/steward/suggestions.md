# Steward alignment suggestions for `ghafi`

> Authored by `steward` (the AgentCulture alignment scaffold) after a read-only
> audit of the current `ghafi` tree against its sibling repos `../afi-cli`,
> `../cfafi`, and `../steward`. This document is a recommendation, not a patch.
> Nothing in `ghafi` has been changed by writing this file other than the file
> itself.

## 1. Why this file exists

`ghafi` is a designated AgentCulture sibling — a repo that is expected to wear
the same scaffold as the rest of the family (`afi-cli` is the pattern source,
`cfafi` is a worked example of someone applying the pattern, `steward` is the
alignment authority and skills supplier). Today `ghafi` is at the
"evidence-only scaffold" stage: a deliberate choice, per its `CLAUDE.md`, to
avoid inventing tooling before any real code lands.

`steward`'s job is to reduce the distance between that pre-implementation state
and the agreed AgentCulture sibling shape. This file is `steward`'s recommended
path through that distance: ordered by dependency, with a concrete reference in
a sibling repo for every step, plus an honest section on what `steward` itself
is missing before it can do this work for you with a single command.

## 2. Current state — audited

What `ghafi` ships today (everything tracked on the `add-claude-md` branch,
which is the latest scaffolding work):

- `README.md` — three lines, one-sentence tagline.
- `CLAUDE.md` — 26 lines, declares the repo at "scaffolding stage", forbids
  inventing tooling/commands, treats workspace siblings as tentative.
- `LICENSE` — MIT, copyright agentculture 2026.
- `.gitignore` — Python-oriented but not committing to a toolchain.
- `.claude/settings.local.json` — local permissions allowlist (python3, git,
  `gh pr create`).

What is **absent** vs. an aligned AgentCulture sibling (concrete deltas, not
speculation — every item below is something at least one of `../afi-cli`,
`../cfafi`, or `../steward` has and `ghafi` does not):

- No `pyproject.toml` (no project name, version, deps, entry point).
- No top-level Python package and no `__main__` module.
- No `cli/` package implementing the afi-cli scaffold pattern (`_errors.py`,
  `_output.py`, `_commands/`).
- No `tests/` directory.
- No `.github/workflows/` (no CI, no publish pipeline).
- No `CHANGELOG.md` (no Keep-a-Changelog history).
- No `.claude/skills/` (no portable, scripted automations — only the local
  permission file is present).
- No `.claude/skills.local.yaml.example` (no documented per-machine config
  schema).
- No repo-local lint configs (`.flake8`, `.markdownlint-cli2.yaml`).

## 3. Alignment checklist (dependency-ordered)

Each item: *what to add*, *where it lives*, *why*, and a **Reference** pointer
to the equivalent file in a sibling repo. Land them in this order — later
items assume earlier ones.

1. **Toolchain decision.** Adopt `uv` + `pyproject.toml` (hatchling backend),
   Python ≥3.12, zero runtime deps where possible. Project name on PyPI:
   `ghafi-cli`. Binary: `ghafi`. *Why:* matches every other AgentCulture
   sibling and unlocks Trusted Publishing later.
   *Reference:* `../cfafi/pyproject.toml`, `../steward/pyproject.toml`.

2. **Package skeleton.** Top-level `ghafi/` package containing `__init__.py`
   (which reads `__version__` via `importlib.metadata("ghafi-cli")` rather
   than holding a literal) and `__main__.py` (so `python -m ghafi` works).
   *Why:* no second source of truth for the version; CI version-check stays
   simple.
   *Reference:* `../steward/steward/__init__.py`, `../steward/steward/__main__.py`.

3. **CLI scaffolding (afi-cli pattern).** Create `ghafi/cli/__init__.py`
   exporting `_GhafiArgumentParser`, `_build_parser()`, `_dispatch()`, and
   `main()`. Add `cli/_errors.py` with a `GhafiError` exception and exit-code
   constants — mirror `cfafi`'s extended set since `ghafi` will talk to a
   remote API: `0` success, `1` user error, `2` env error, `3` auth error,
   `4` API error. Add `cli/_output.py` with `emit_result()` and
   `emit_error()` helpers, a strict stdout/stderr split, and `--json` mode.
   *Why:* the afi-cli pattern is the AgentCulture contract — agents can drive
   any CLI that follows it without bespoke parsing.
   *Reference:* `../afi-cli/afi/cite/references/python-cli/` (canonical
   template with `{{slug}}`/`{{module}}` tokens) and `../cfafi/cfafi/cli/`
   (a real implementation).

4. **First commands.** Add `ghafi/cli/_commands/{learn,explain,whoami}.py`,
   each exposing `register(sub)`. `learn` is the agent-self-teaching prompt
   (text and `--json`). `explain` documents nouns/verbs. `whoami` verifies
   GitHub auth — call `gh auth status` if `gh` is on `PATH`, otherwise hit
   `GET /user` with the `GITHUB_TOKEN`/`GH_TOKEN` env var. *Why:* `learn` and
   `explain` are the agent-first affordances every AgentCulture CLI ships;
   `whoami` is the smallest read-only surface that proves the auth chain.
   *Reference:* `../cfafi/cfafi/cli/_commands/whoami.py` (cfafi's auth probe
   for CloudFlare; same shape applies to GitHub).

5. **Mutation safety.** Any `ghafi` verb that writes to GitHub (issues, PRs,
   labels, repo settings) defaults to dry-run and requires `--apply` to
   commit. Print the would-be request body in dry-run. *Why:* `ghafi` is
   "GitHub CLI and agent" — agents can and will call it in loops; safe
   defaults are the difference between a useful tool and a foot-gun.
   *Reference:* `../cfafi/cfafi/cli/_commands/dns.py` (the dry-run /
   `--apply` pattern, applied to a different remote API).

6. **Tests.** Create `tests/` with one `test_cli_<verb>.py` per command,
   `test_errors.py`, `test_output.py`, and a `conftest.py`. Use pytest with
   `pytest-xdist` for parallel runs. Mock the GitHub API at the `urllib`
   level so tests have no network dependency. *Why:* CI gates everything
   that follows; without tests there is no version-check, no publish.
   *Reference:* `../cfafi/tests/`.

7. **CI workflows.** Add `.github/workflows/tests.yml` (pytest + `black`,
   `isort`, `flake8`, `bandit`, `markdownlint-cli2`, plus a version-check
   job that fails when `pyproject.toml`'s version equals `main`'s) and
   `.github/workflows/publish.yml` (Trusted Publishing to PyPI on push to
   `main`; `.dev<run_number>` to TestPyPI on PRs from non-fork branches).
   *Why:* the version-check is an AgentCulture rule — every PR bumps the
   semver, no exceptions; the publish workflow uses OIDC so no API tokens
   live in the repo.
   *Reference:* `../steward/.github/workflows/tests.yml`,
   `../steward/.github/workflows/publish.yml`.

8. **CHANGELOG.** Add `CHANGELOG.md` in Keep-a-Changelog format (one
   `## [x.y.z] - YYYY-MM-DD` heading per release with `### Added` / `###
   Changed` / `### Fixed` subsections). The version-bump skill (next item)
   prepends to it automatically.
   *Reference:* `../steward/CHANGELOG.md`.

9. **Skills.** Vendor `.claude/skills/version-bump/` from `../steward`
   verbatim — the `bump.py` script edits `pyproject.toml` and prepends a
   CHANGELOG entry, with no external dependencies. Vendor
   `.claude/skills/pr-review/` from `../steward` and then narrow it to
   `ghafi`'s reviewers (Qodo/Copilot wiring, portability lint, etc.). Add
   `.claude/skills.local.yaml.example` documenting any per-machine paths
   `ghafi` needs (likely none yet — but the file is the contract). Each
   skill must follow the `steward` skills convention: `SKILL.md` + a
   `scripts/` entry-point, **no external path dependencies** (no reaching
   into per-user home-directory dotfiles, no absolute paths into other
   sibling checkouts —
   if a skill needs something from elsewhere, vendor it). *Why:* portability
   across Culture machines is the whole point of the convention; a skill
   that breaks because another repo isn't checked out at a specific path is
   not a skill, it is a local hack.
   *Reference:* `../steward/.claude/skills/version-bump/`,
   `../steward/.claude/skills/pr-review/`,
   `../steward/.claude/skills.local.yaml.example`,
   and the "Skills convention" section of `../steward/CLAUDE.md`.

10. **Lint configs.** Add `.flake8` and `.markdownlint-cli2.yaml` at the
    repo root. The markdown config must be repo-local; do **not** rely on a
    per-user home-directory config — that is the precise portability
    failure the skills convention is designed to prevent.
    *Reference:* `../steward/.flake8`, `../steward/.markdownlint-cli2.yaml`.

11. **`CLAUDE.md` rewrite (last, not first).** Once items 1–10 land, replace
    the "TBD; not yet declared in-tree" toolchain section with the real
    install/run/test/lint commands, document the GitHub-auth strategy
    (env-var precedence, `gh` fallback), name the AgentCulture integration
    boundaries (what `ghafi` does and does not do for the mesh), and drop
    the "do not invent commands" guard. *Why:* the guard exists because the
    repo had no toolchain to point at — once it does, the guard is what is
    inventing fiction. Keep the workspace-relative path discipline ("repo
    rather than absolute") that the current `CLAUDE.md` already enforces.

## 4. Gaps preventing fully-scripted alignment from `steward`

The checklist above is prose. The user asked what is missing before
`steward` could run, e.g., `steward align ../ghafi` and produce that
checklist as a series of script-driven changes against the target repo.
Honest inventory:

### 4.1 Missing in `steward`

- **No `align` subcommand.** `../steward/steward/cli/_commands/` currently
  contains only `show.py` (which wraps the `agent-config` skill). There is
  no verb that takes a sibling-repo path, audits it, and either reports or
  emits the alignment delta.
  *Suggested next step:* add `steward/cli/_commands/align.py` whose initial
  surface is `steward align <path> [--json] [--apply]`. Without `--apply`
  it prints the checklist above as structured findings; with `--apply` it
  starts emitting (see next item).
- **No scaffold-emission engine.** `../afi-cli/afi/cite/_engine.py` already
  knows how to render a templated CLI tree (`{{slug}}`/`{{module}}` token
  expansion) into a target directory. `steward` does not consume that
  engine, so steps 2–4 of the checklist cannot be executed by code today.
  *Suggested next step:* depend on (or vendor) `afi-cli`'s cite engine and
  call it from `steward align --apply` for items 2–4. Treat `afi-cli` as
  the upstream of the CLI template and `steward` as the policy layer that
  decides which template version a given sibling should be on.
- **No rubric/checks runner.** `../afi-cli/afi/rubric/` scores a repo
  against the afi-cli pattern (learnability, JSON, error handling,
  structure). `steward` has no equivalent — there is no machine-readable
  pass/fail for "is this sibling aligned." The portability lint inside
  `../steward/.claude/skills/pr-review/scripts/portability-lint.sh` is
  bash, scoped to a PR diff, and not exposed as a `steward` verb.
  *Suggested next step:* add `steward/rubric/` mirroring `afi-cli`'s
  bundle layout; expose as `steward verify <path>` returning a structured
  report and a non-zero exit on any failed check. Promote the bash
  portability lint to one of those checks (`steward verify --check
  portability`).
- **No alignment-state file.** `steward` keeps no record of which siblings
  it has audited, when, or which checklist items are done. Re-running an
  alignment is a manual diff each time.
  *Suggested next step:* on `steward align --apply`, write
  `<sibling>/.steward/alignment.json` recording the rubric version, the
  template revision applied, and per-item status. Subsequent runs read
  that file and only emit deltas.
- **No backend-parity check for skills.** `steward`'s `CLAUDE.md` says
  "when a skill stabilizes here, the next step is propagating it to
  sibling projects … the all-backends rule applied to skills." There is no
  script today that asks "which skills exist in `steward` but not in
  `<sibling>`" or vice versa.
  *Suggested next step:* `steward skills diff <path>` — compare
  `.claude/skills/` directory contents (by SKILL.md frontmatter `name`)
  between `steward` and the target.

### 4.2 Missing in `ghafi` for `steward` to act on

- **No `pyproject.toml` to read a package name from.** `steward align`
  needs to know the target's package and binary name to render templates.
  Until item 1 of the checklist lands manually (or is added by the engine
  with sensible defaults), `--apply` has nothing to anchor on.
- **No `.claude/skills.local.yaml`.** Once `ghafi` has skills, `steward`
  needs a documented per-machine config schema to know e.g. where
  `ghafi`'s GitHub credentials come from on this host. The committed
  `.example` file is the contract; the git-ignored real file is the
  per-machine instance.
- **No agreed upstream-skill source.** When the same skill exists in both
  `../steward` and `../afi-cli` (e.g. `version-bump`), there is currently
  no recorded convention saying which one is canonical. `steward align`
  cannot deterministically pick a source.
  *Suggested next step:* add a short `docs/skill-sources.md` to `steward`
  declaring, per skill, which repo is the upstream and what the
  vendor-vs-cite policy is.

### 4.3 Missing org-wide

- **No machine-readable manifest of the AgentCulture sibling pattern.**
  The checklist in §3 lives only in prose, in this file, in
  `../afi-cli/docs/agent-first.md`, and implicitly in
  `../steward/CLAUDE.md`. `afi-cli`'s rubric is the closest thing to a
  contract, but it is not published as a versioned schema that
  `steward align` could consume.
  *Suggested next step:* publish a single source-of-truth schema (e.g.
  `agentculture-sibling-pattern.json`) that names each required artifact,
  its location pattern, the rubric checks that validate it, and the repo
  version it targets. `steward` and `afi-cli` would both consume it.

## 5. Verification (manual today, scripted tomorrow)

Until `steward verify <path>` exists, an aligned `ghafi` is one where all
of these hold:

- `uv sync` (from a clean checkout) succeeds.
- `uv run ghafi --version` prints the version from `pyproject.toml`.
- `uv run python -m ghafi --version` agrees.
- `uv run ghafi learn` returns a structured prompt; `uv run ghafi learn
  --json` parses as JSON.
- `uv run ghafi explain <known-noun>` returns the registered help text;
  unknown nouns exit non-zero with a structured error (not a Python
  traceback).
- `uv run ghafi whoami` exits `0` against a valid `GITHUB_TOKEN` and `3`
  against a missing/invalid one.
- Any GitHub-write verb defaults to dry-run; `--apply` is required to
  observe a side effect.
- `uv run pytest -n auto -v` passes.
- `markdownlint-cli2 "**/*.md"` is clean against the repo-local config.
- `.github/workflows/tests.yml` runs green on a PR; the version-check job
  fails when `pyproject.toml`'s version equals `main`'s.
- `.github/workflows/publish.yml` publishes to TestPyPI on PRs and to PyPI
  on push to `main`.
- `.claude/skills/<name>/` for each skill contains `SKILL.md` + a
  `scripts/` entry-point, and `grep -RnE '/home/|~/\.claude' .claude/`
  returns nothing.
- A fresh checkout on a different machine (or in CI) needs only the
  `.example` files plus committed configs to run — no per-user dotfiles
  required.

When `steward verify ../ghafi` and `steward align ../ghafi` exist, this
section becomes a single command and a non-zero exit code on the first
divergence.

- Claude
