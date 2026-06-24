---
name: mass-approve-prs
description: >
  Approve many pull requests at once across a whole GitHub org (or one repo),
  selecting them by a title heading. Composes two gitculture verbs —
  `gitculture pr list` (read-only org-wide search) to discover the matches and
  `gitculture pr approve` (one approving review each) to act — so it inherits
  gitculture's dry-run-default mutation safety: it shows every PR it *would*
  approve before you pass --apply. Per-PR failures (most often "can't approve
  your own pull request") are tallied, not fatal. Use when: a bot opened the
  same PR across many repos (a dependency bump, a skills sync, a CI change)
  and you want to approve all the still-open ones in one pass.
---

# Mass-approve PRs by title

When an agent or automation opens the *same* PR across every repo in an org —
"Bump X to Y", "Add eidetic remember/recall memory skills", a CI-config sync —
approving them one-by-one in the GitHub UI is slow and error-prone. This skill
finds them by title and approves them together, with a dry-run you actually
look at first.

## The shape (why two verbs, not one)

- **Discovery is read-only.** `gitculture pr list <org> --title <…>` scans the
  org via the GitHub Search API and re-checks each title client-side (the Search
  API's `in:title` is fuzzy, so an exact/prefix re-check kills false
  positives). Nothing is written.
- **Approval is one reviewable mutation per PR.** `gitculture pr approve
  <owner>/<repo> <number>` submits a single `APPROVE` review, dry-run by
  default. Keeping the write verb single-PR is deliberate: every mutation is
  inspectable, and a batch can't half-apply some giant opaque change.

The script just loops the second over the output of the first.

## Run it

Always dry-run first and read the matched list:

```bash
# Dry-run: list matches + show the approval each would get. No writes.
.claude/skills/mass-approve-prs/scripts/mass-approve-prs.sh \
  --org agentculture --title "Add eidetic remember/recall memory skills"

# Looks right? Approve them all:
.claude/skills/mass-approve-prs/scripts/mass-approve-prs.sh \
  --org agentculture --title "Add eidetic remember/recall memory skills" --apply
```

Useful flags:

- `--match exact|prefix|substring` — how `--title` is compared
  (case-insensitive, whitespace-stripped). Default `exact`; use `prefix` when
  the heading is a stable start but repos append a suffix, `substring` to cast
  wider. Start strict, widen only if the dry-run under-matches.
- `--state open|closed|all` — default `open` (the usual "approve the ones
  still open").
- `--repo NAME` — restrict to one repo (lists its pulls directly instead of
  searching the org).
- `--body "<note>"` — the review comment posted with each approval. Defaults to
  a signed note (`Approved via gitculture mass-approve-prs skill. — Claude`) so
  it's clear an assistant approved; pass `--body ""` for a bare approval.

## Reading the result

The dry-run prints the matched PRs (`owner/repo#number (author) title`) and, per
PR, the JSON body it would POST. The apply run prints a summary:

```text
=== Summary ===
  approved: 7
  skipped:  1  (self-authored)
  failed:   0
```

- **skipped (self-authored)** — GitHub forbids approving your *own* PR (HTTP
  422). If the bot that opened the PRs is the same identity as your token,
  every PR will skip; approve with a different account.
- **failed** — anything else (permissions, a closed PR, transport). The script
  keeps going and exits non-zero at the end so CI/automation notices.

## Requirements

- `python3` (stdlib only — used to parse `pr list --json`).
- `gitculture` on PATH, or run from the `ghafi` checkout (the script falls back
  to `uv run --project <repo> gitculture`).
- Auth via `GITHUB_TOKEN` / `GH_TOKEN`; the script bridges `gh auth token` when
  neither is set. Approving needs the `repo` scope (classic PAT) or a
  fine-grained token with **Pull requests: write**.

## Notes

- Re-running approves again (GitHub allows multiple reviews per PR); it is not
  idempotent, but a second identical approval is harmless.
- This approves — it does not merge. Merging stays a separate, deliberate step.
