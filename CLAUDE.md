# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ghafi** — GitHub CLI and agent; an AgentCulture manager (per `README.md`).

The repo is at the scaffolding stage. There is no source code, build system, test suite, or version manifest yet. Treat any "command to run" question as unanswered until the relevant tooling is actually added — do not invent commands.

## Workspace context (tentative)

This repository may be checked out as part of a larger multi-project workspace. If so, consult the workspace-root docs for shared conventions; nothing in *this* repo currently proves any particular sibling-project relationships, interoperability requirements, or backend-parity rules.

The README's tagline ("AgentCulture manager") suggests ghafi is intended as a GitHub-side companion to an agent-mesh project, but treat that as author intent rather than a requirement until matching code or specs land in-tree.

## Toolchain (TBD; not yet declared in-tree)

The current tree does not declare a toolchain. The `.gitignore` is largely Python-oriented, but that alone is not enough to commit to a language or package manager.

When a toolchain is chosen, document it here — entry point, install command, test command, lint command — and remove this TBD note. Until then, do not add runnable setup/test command blocks to this file.

## When the repo grows

Update this file with the *non-obvious* things future Claude instances will need: the actual CLI entry point, how ghafi authenticates to GitHub, what (if anything) it manages on the AgentCulture side, and any invariants (e.g., "ghafi never writes to a repo without `--confirm`"). Skip anything discoverable from a 30-second `ls` or `pyproject.toml` read, and prefer repo-relative references over absolute or home-directory paths so the guidance stays portable across contributors and CI.
