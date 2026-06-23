---
name: mass-merge-prs
description: >
  Merge many pull requests at once across a whole GitHub org (or one repo),
  selecting them by a title heading. Composes two ghafi verbs — `ghafi pr list`
  (read-only org-wide search) to discover the matches and `ghafi pr merge` (one
  direct merge each) to act — so it inherits ghafi's dry-run-default mutation
  safety: it shows every PR it *would* merge before you pass --apply. Uses the
  direct merge endpoint (like `gh pr merge --admin`), so it lands PRs past
  NON-required failing checks such as a non-blocking `lint`; PRs blocked by a
  required check are tallied, not fatal. Use when: a bot opened the same PR
  across many repos (a rollout, a dependency bump, a skills sync) and you want
  to land all the still-open ones in one pass — especially when self-approval
  is impossible (the author is your own account) so merging is the only way to
  ship them.
---

# Mass-merge PRs by title

The companion to `mass-approve-prs`. When the same PR is opened across every
repo in an org — a rollout branch, a dependency bump, a skills sync — and you
want them *landed*, this finds them by title and merges them together, with a
dry-run you actually look at first.

It is the right tool precisely when **approval won't work**: if every PR was
opened by your own account, GitHub forbids you approving them (HTTP 422), so
the only way to ship is to merge. As a repo admin you can do that directly.

## The shape (why two verbs, not one)

- **Discovery is read-only.** `ghafi pr list <org> --title <…>` scans the org
  via the GitHub Search API and re-checks each title client-side (the Search
  API's `in:title` is fuzzy). Nothing is written.
- **Merge is one reviewable mutation per PR.** `ghafi pr merge
  <owner>/<repo> <number>` PUTs the direct merge endpoint, dry-run by default.

The script loops the second over the output of the first.

## What "direct merge" clears (and what it doesn't)

`ghafi pr merge` uses `PUT /repos/{owner}/{repo}/pulls/{number}/merge` — the
same path as `gh pr merge --admin`:

- **Clears non-required failing checks.** A failing `lint` that isn't a
  *required* status check shows in the UI as an "unstable"/red merge button but
  does not actually block the merge endpoint. These merge fine.
- **Does NOT bypass required checks** when branch protection includes
  administrators. Those return HTTP 405 and are tallied as **blocked** — fix by
  relaxing protection or satisfying the required check, then re-run.

## Run it

Always dry-run first and read the matched list:

```bash
# Dry-run: list matches + show the merge each would get. No writes.
.claude/skills/mass-merge-prs/scripts/mass-merge-prs.sh \
  --org agentculture --title "Add eidetic remember/recall memory skills"

# Looks right? Merge them all (squash by default):
.claude/skills/mass-merge-prs/scripts/mass-merge-prs.sh \
  --org agentculture --title "Add eidetic remember/recall memory skills" --apply
```

Useful flags:

- `--method squash|merge|rebase` — merge method (default `squash`).
- `--match exact|prefix|substring` — how `--title` is compared
  (case-insensitive). Default `exact`; widen only if the dry-run under-matches.
- `--state open|closed|all` — default `open`.
- `--repo NAME` — restrict to one repo.

## Reading the result

The apply run prints a summary:

```text
=== Summary ===
  merged:   51
  blocked:   1  (conflict, or required check / branch protection)
  failed:    0
```

- **blocked** — the PR is not mergeable (HTTP 405). Two common causes: a
  **merge conflict** with the base branch (the PR is `DIRTY`/`CONFLICTING` — an
  admin merge can't fix this; rebase and resolve the conflict), or a *required*
  check / admin-locked branch protection. Resolve, then re-run; the
  already-merged PRs simply drop out of the next match.
- **failed** — anything else (permissions, conflict, transport). The script
  keeps going and exits non-zero so automation notices.

## Requirements

- `python3` (stdlib only), and `ghafi` on PATH (or run from the checkout).
- Auth via `GITHUB_TOKEN` / `GH_TOKEN`; the script bridges `gh auth token`.
  Merging needs `repo` (classic PAT) or fine-grained **Contents: write** +
  **Pull requests: write**. Forcing past a *required* check additionally needs
  admin on the repo.

## Notes

- This merges — it is the deliberate, less-reversible step. Run the dry-run and
  read the list every time.
- Already-merged PRs are not in the `open` match set on a re-run, so the script
  is naturally resumable.
