---
name: actions-usage
description: >
  Audit GitHub Actions minute consumption across an org and explain *why* the
  included-minutes quota (3000/mo on Team) is being drawn down. Joins the
  enhanced-billing usage API against each repo's private/public flag and
  weights by runner-OS multiplier (Linux x1, Windows x2, macOS x10), so the
  real cost drivers surface — only PRIVATE repos count against the quota, and
  a small macOS matrix leg can outweigh a busy Linux repo. Use when: the org
  is near its Actions limit, the bill spikes, or someone asks "why are we at
  N% of our minutes / where are our CI minutes going".
---

# Actions usage audit

The GitHub billing dashboard shows a single "X% of 3000 minutes" bar with no
breakdown. This skill reconstructs the breakdown so you can act on it.

## The model (why a naive read misleads)

- **Public repos = unlimited free minutes.** Their usage shows in the billing
  API with a full discount (`netAmount: 0`) but **never** touches the quota.
  Don't chase a public repo with huge raw minutes — it costs nothing.
- **Only PRIVATE repos draw down the 3000-minute included allotment.**
- **Runner OS multiplies quota cost:** Linux ×1, Windows ×2, **macOS ×10**.
  A repo with 56 raw macOS minutes burns 560 quota minutes — it can rank #2
  on cost while looking trivial by raw minutes.

So the question "why are we at the limit" = "which **private** repos have the
most **quota-weighted** minutes this month," which is exactly what the script
computes.

## Run it

```bash
# Org-wide breakdown for the current month (default org: agentculture)
.claude/skills/actions-usage/scripts/actions-usage.sh

# A specific month
.claude/skills/actions-usage/scripts/actions-usage.sh --month 2026-06

# Drill into the top consumer: run counts by workflow + trigger event
.claude/skills/actions-usage/scripts/actions-usage.sh --month 2026-06 --repo colleague

# Raw billing JSON (for ad-hoc jq)
.claude/skills/actions-usage/scripts/actions-usage.sh --json
```

## Requirements

- `gh` (authenticated), `jq`, `awk`.
- The enhanced-billing usage endpoint
  (`/organizations/{org}/settings/billing/usage`) needs **`admin:org`** — the
  legacy `/settings/billing/actions` endpoint was retired (HTTP 410), and
  `read:org` alone returns 403. If you hit a scope error:

  ```bash
  gh auth refresh -h github.com -s admin:org
  ```

## Reading the output

`weighted` is quota cost (what matters); `raw` is wall-clock minutes. When
`weighted ≫ raw`, the repo is on Windows/macOS runners — the cheapest fix is
usually trimming the OS matrix. When a repo's run **count** is the problem
(seen via `--repo`), look for workflows firing on both `push` and
`pull_request` (e.g. a publish-to-TestPyPI-on-PR doubling every push), or a
high commit/PR velocity.

## Levers once you've found the driver

- Drop `macos-latest` / `windows-latest` from a test matrix that doesn't need
  them (kills the ×10 / ×2 weight).
- Gate publish/heavy workflows so they don't run on every PR.
- Add `concurrency:` with `cancel-in-progress: true` to kill superseded runs.
- `paths:` / `paths-ignore:` filters so doc-only commits skip CI.
- Consider making low-sensitivity repos public (unlimited free minutes).
