### CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ghafi** — GitHub CLI and agent; an AgentCulture manager.

The repo is at the scaffolding stage: only `README.md`, `LICENSE`, and `.gitignore` exist. There is no source code, build system, test suite, or version manifest yet. Treat any "command to run" question as unanswered until the relevant tooling is actually added — do not invent commands.

## Context within the workspace

`/home/spark/git/` is a multi-project workspace (see `/home/spark/git/CLAUDE.md`). ghafi sits alongside the **culture** project ("IRC-based agent mesh where AI agents collaborate peer-to-peer"); ghafi's tagline "AgentCulture manager" suggests it is intended as a GitHub-side companion / management CLI for that mesh. When designing APIs, naming, or workflows here, look at `culture/` for the conventions ghafi will need to interoperate with — especially the all-backends rule (`claude` / `codex` / `copilot` / `acp` parity) if ghafi ends up wrapping agent backends.

## Toolchain (implied, not yet in tree)

The `.gitignore` is the standard Python template (`__pycache__/`, `*.egg-info/`, `build/`, `dist/`, `.venv/`, etc.), so this is a Python project. Workspace convention is **uv** for dependency management:

```bash
uv venv && uv pip install -e ".[dev]"
pytest
```

Adopt the same when adding `pyproject.toml`. Don't introduce a different package manager (poetry, pipenv, plain pip-tools) without a reason.

## Conventions inherited from the workspace

- **Linting (Python):** `flake8`, `pylint`, `bandit -r src/`, `black`, `isort`.
- **Linting (Markdown):** `markdownlint-cli2 "path/to/file.md"` (config at `~/.markdownlint-cli2.yaml`).
- **Versioning:** sibling projects (culture, daria) use a `/version-bump` slash command that updates `pyproject.toml` + `__init__.py` + `CHANGELOG.md` before each PR; mirror that pattern once a version manifest exists.
- **Git workflow:** branch → implement → bump version → PR → address review → merge.

## When the repo grows

Update this file with the *non-obvious* things future Claude instances will need: the actual CLI entry point, how ghafi authenticates to GitHub, how it discovers/talks to a culture mesh, and any invariants (e.g., "ghafi never writes to a repo without `--confirm`"). Skip anything discoverable from a 30-second `ls` or `pyproject.toml` read.
