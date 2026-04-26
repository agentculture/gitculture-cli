# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
