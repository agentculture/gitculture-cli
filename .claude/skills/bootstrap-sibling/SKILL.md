---
name: bootstrap-sibling
description: >
  Bootstrap a new aligned AgentCulture sibling end-to-end: GitHub repo
  create, local clone, afi-cli scaffold, and pypi/testpypi Trusted-Publishing
  Environments. Each ghafi step dry-runs first and waits for confirmation
  before applying. Use when starting a new sibling (e.g. "bootstrap a new
  sibling called X", "create a new agentculture repo", "stand up the next
  sibling").
---

# Bootstrap Sibling

Single-command bootstrap for a new AgentCulture sibling repo. Chains the
four steps documented in the project's `CLAUDE.md` ("Bootstrap walkthrough
(new sibling)") with dry-run-then-apply gates, so an agent or human can
drive a full sibling stand-up without remembering the verb order.

The script does **not** automate the PyPI-side trusted-publisher
registration — that's a one-time web flow per project, and ghafi by design
cannot perform it. The script prints the PyPI registration URLs at the end
as a checklist.

## When to use

- Standing up a brand-new sibling under the `agentculture` org.
- After every `ghafi` release, to verify the bootstrap path still works
  end-to-end against a throwaway repo name.

## When **not** to use

- Modifying an existing sibling — use the individual `ghafi repo …` verbs.
- Repos outside the AgentCulture org with non-default conventions.

## Usage

Run from the `ghafi` repo root. The script will `git clone` the new repo
into a sibling path next to ghafi (`../<name>`).

```bash
bash .claude/skills/bootstrap-sibling/scripts/bootstrap.sh \
  --name <repo-name> \
  --description "<one-line description>" \
  [--org agentculture] \
  [--private]
```

Without `--apply`, every ghafi step prints its dry-run output and the
script exits before mutating anything. Pass `--apply` (after reviewing the
dry-run) to commit:

```bash
bash .claude/skills/bootstrap-sibling/scripts/bootstrap.sh \
  --name <repo-name> --description "..." --apply
```

## What the script does

1. `ghafi repo create --org <org> --description "<…>" <name>` — POST `/orgs/{org}/repos`.
2. `git clone https://github.com/<org>/<name>.git ../<name>` — local clone next to ghafi.
3. `ghafi repo scaffold ../<name>` — shells to `afi cli cite`; writes the
   reference template under `.afi/reference/python-cli/`. **Note:** this
   does not instantiate `{{slug}}` into a runnable package; that's a
   follow-up the script does not perform.
4. `ghafi repo env --owner <org> --name pypi --branch main <name>` — PUT pypi env (main only).
5. `ghafi repo env --owner <org> --name testpypi <name>` — PUT testpypi env (any branch).
6. Prints a manual checklist: register the trusted publisher on pypi.org
   and test.pypi.org pointing at `<org>/<name>`, workflow `publish.yml`.

If `GITHUB_TOKEN` and `GH_TOKEN` are both unset, the script bridges from
`gh auth token` so users with `gh` already authenticated don't need a
separate PAT.
