---
name: doc-test-align
description: >
  Verify that claims in CLAUDE.md (GitHub endpoints, required scopes,
  bootstrap step order) still match what the code in `ghafi/` actually
  does. Run before merging anything that touches CLAUDE.md or the
  `ghafi.cli._commands.repo` module — catches doc drift that a normal
  pytest pass would not.
---

# Doc / Test Alignment

A small, opinionated drift detector. CLAUDE.md makes empirical claims
about external systems — which GitHub REST endpoints `ghafi` calls,
which token scopes those calls require, what step order the bootstrap
walkthrough specifies. The mutation-safety pytest catches code regressions;
this skill catches the *documentation* equivalent.

This is a **stub** — v0 covers a narrow set of claims. Extend the script
when a new failure mode is found.

## When to use

- Reviewer is about to approve a PR that touches `CLAUDE.md`,
  `ghafi/cli/_commands/repo.py`, or `ghafi/_api.py`.
- Before cutting a release.
- Periodically (e.g. quarterly) as a sweep to catch silent drift from
  GitHub API changes.

## What it checks (v0)

1. **Endpoint mentions in CLAUDE.md exist in code.** Every `/repos/...`,
   `/orgs/...`, `/user/...` URL referenced in CLAUDE.md should appear
   somewhere in `ghafi/`. Strings only — does not validate semantics.
2. **Bootstrap step list matches verb set.** The "Bootstrap walkthrough"
   section should reference the same `repo {create,scaffold,env}` verbs
   that `ghafi/cli/_commands/repo.py` registers, and no others.
3. **Scope list claim is empirically backed.** If CLAUDE.md says scope
   X is required, there should be a comment/test/CHANGELOG entry showing
   it was tested. (v0 just lists scopes for human review; v1 should diff
   against an `_api` annotation.)

## What it does **not** check

- Whether GitHub's actual scope requirements have changed upstream
  (would require live API calls).
- Whether endpoint payloads still match GitHub's current schema.
- Prose accuracy beyond URLs and verb names.

These are deferred to a future revision; the user should add cases as
real drift is observed.

## Usage

```bash
bash .claude/skills/doc-test-align/scripts/check.sh
```

Exit codes:

- `0` — no drift detected.
- `1` — drift detected; details printed to stdout.
- `2` — script error (missing files, bad invocation).

The script is grep-and-compare only; no network, no test runs. Pair it
with the existing `markdownlint-cli2` and `portability-lint.sh` checks
in CI when you trust the v1 surface.
