"""Mutation-safety contract.

Every verb that writes state — to GitHub or the local file system —
must expose ``--apply`` defaulting to False, and must not perform any
write when ``--apply`` is absent. CLAUDE.md describes the contract;
this module enforces it programmatically so the "flag it manually in
code review" gap is closed for every new mutating verb.
"""

from __future__ import annotations

import argparse

import pytest

from ghafi.cli import _build_parser
from ghafi.cli import main as cli_main

# Subcommands that mutate state (GitHub or local FS) and therefore must
# expose --apply defaulting to False. Add new mutating verbs here when
# they're introduced.
MUTATING_VERBS: list[list[str]] = [
    ["repo", "create"],
    ["repo", "scaffold"],
    ["repo", "env"],
]

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _walk_to_leaf(parser: argparse.ArgumentParser, path: list[str]) -> argparse.ArgumentParser:
    target = parser
    for token in path:
        sub_action = next(
            (a for a in target._actions if isinstance(a, argparse._SubParsersAction)),
            None,
        )
        assert sub_action is not None, f"no sub-action under {target.prog!r} for {token!r}"
        assert token in sub_action.choices, f"{token!r} not in {list(sub_action.choices)}"
        target = sub_action.choices[token]
    return target


def _find_apply(parser: argparse.ArgumentParser) -> argparse.Action | None:
    for action in parser._actions:
        if "--apply" in action.option_strings:
            return action
    return None


@pytest.mark.parametrize("verb", MUTATING_VERBS, ids=lambda v: " ".join(v))
def test_mutating_verb_has_apply_default_false(verb: list[str]) -> None:
    """Structural: --apply exists on every mutating verb and defaults to False."""
    leaf = _walk_to_leaf(_build_parser(), verb)
    apply_action = _find_apply(leaf)
    assert apply_action is not None, f"`ghafi {' '.join(verb)}` is missing --apply"
    assert (
        apply_action.default is False
    ), f"`ghafi {' '.join(verb)}` --apply default must be False, got {apply_action.default!r}"


def test_repo_create_dry_run_does_not_call_api(http_stub) -> None:
    """Behavioral: dry-run `repo create` performs no HTTP writes."""
    rc = cli_main(["repo", "create", "demo", "--org", "agentculture"])
    assert rc == 0
    writes = [(m, p) for (m, p, _payload, _q) in http_stub.calls if m in WRITE_METHODS]
    assert writes == [], f"dry-run leaked writes: {writes}"


def test_repo_env_dry_run_does_not_call_api(http_stub) -> None:
    """Behavioral: dry-run `repo env` performs no HTTP writes."""
    rc = cli_main(["repo", "env", "demo", "--owner", "agentculture"])
    assert rc == 0
    writes = [(m, p) for (m, p, _payload, _q) in http_stub.calls if m in WRITE_METHODS]
    assert writes == [], f"dry-run leaked writes: {writes}"


def test_repo_scaffold_dry_run_does_not_invoke_afi(afi_stub) -> None:
    """Behavioral: dry-run `repo scaffold` does not shell out to afi."""
    rc = cli_main(["repo", "scaffold", "/tmp/demo"])
    assert rc == 0
    assert afi_stub.calls == [], f"dry-run leaked subprocess calls: {afi_stub.calls}"
