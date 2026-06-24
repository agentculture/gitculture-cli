---
name: pr-review
description: >
  gitculture PR workflow: branch, commit, push, PR, wait for review (Qodo +
  Copilot), triage, fix, reply, resolve. Includes a portability lint (no
  absolute /home paths, no per-user dotfile refs in committed docs) and a
  dry-run-default reminder for any GitHub-mutating change. Use when: creating
  PRs in this repo (agentculture/gitculture-cli), handling review feedback, or the user says "create PR",
  "review comments", "address feedback", "resolve threads".
---

# PR Review — gitculture edition

`gitculture`'s PRs touch GitHub-API surface (repo creation, environments,
permissions) and AgentCulture conventions (afi-cli scaffold contract,
Trusted Publishing wiring). The recurring bug classes:

- **Path leaks** — committing absolute home-directory paths that work only on
  the author's machine. `scripts/portability-lint.sh` catches these.
- **Per-user config dependencies** — referencing dotfiles under `~/` in repo
  guidance, breaking reproducibility for other contributors and CI.
- **Forgotten dry-run** — any new GitHub-mutating verb must default to
  dry-run; `--apply` commits. This is enforced in code review (no automated
  check yet — flag it manually for any new `repo` / future `pr` / future
  `issue` verb).

## Prerequisites

`gh` (GitHub CLI), `bash`, `python3` (stdlib only). The portability lint
runs against `git ls-files` or the staged-vs-HEAD diff; no other tooling.

## Portability lint

The single committed script today. Run from the repo root:

```bash
# Lint files modified vs HEAD (default — staged + unstaged):
bash .claude/skills/pr-review/scripts/portability-lint.sh

# Lint every tracked file:
bash .claude/skills/pr-review/scripts/portability-lint.sh --all
```

Exits 0 if clean, 1 if a leak is found. The CI `lint` job runs it with
`--all` on every PR — keep the working tree clean before pushing.

Allowed carve-outs (won't be flagged):

- `~/.claude/skills/<x>/scripts/` — vendored tool calls.
- `~/.culture/` — Culture-mesh data this skill is supposed to read (kept for
  parity with steward; gitculture doesn't use it today).

## End-to-end flow

```text
git checkout -b <type>/<desc>
# ... edit ...
bash .claude/skills/pr-review/scripts/portability-lint.sh
python3 .claude/skills/version-bump/scripts/bump.py {patch|minor|major}
uv run pytest -n auto -v
git commit -am "..." && git push -u origin <branch>
gh pr create --title "..." --body "..."   # title <70 chars; body signed "- Claude"
# Wait for Qodo + Copilot review (~5 min after push).
gh api repos/{owner}/{repo}/pulls/<PR>/comments
# Triage: FIX or PUSHBACK with reasoning per comment.
# Fix, re-lint, push, reply, resolve threads.
gh pr checks <PR>
# Wait for human merge — never merge yourself.
```

Branch naming: `fix/<desc>`, `feat/<desc>`, `docs/<desc>`, `skill/<name>`.
Commit/PR signature: `- Claude` (workspace convention).

## Triage rules

For every comment, decide **FIX** or **PUSHBACK** with reasoning.

Default to **FIX** for: portability complaints (always valid for this project
— recurring bug class), missing dry-run on a GitHub-mutating verb, missing
`learn`/`explain` entry for a new verb, test or doc requests, style nits
aligned with workspace conventions.

Default to **PUSHBACK** for: architecture opinions that conflict with
`CLAUDE.md` (e.g., "add a runtime dep" — `gitculture` is stdlib-only); requests
to add features outside the alignment scope of the current PR.

## Reply etiquette

Every comment must get a reply — no silent fixes. Pass `--resolve` when
batch-replying so threads close automatically. Reference review-comment IDs
in the fix-up commit message.
