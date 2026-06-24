"""gitculture repo env — dry-run body, apply, owner fallback, branch policy."""

from __future__ import annotations

import json

from gitculture.cli import main


def test_env_dry_run_default_pypi(capsys, http_stub):
    http_stub.set("GET", "/user", {"login": "octocat"})
    rc = main(["repo", "env", "myrepo", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is True
    assert "PUT /repos/octocat/myrepo/environments/pypi" in payload["endpoint"]
    assert payload["would_put"]["reviewers"] is None
    assert payload["would_put"]["wait_timer"] == 0
    assert payload["would_put"]["deployment_branch_policy"] is None


def test_env_dry_run_with_branch_sets_custom_policy(capsys, http_stub):
    http_stub.set("GET", "/user", {"login": "octocat"})
    rc = main(["repo", "env", "myrepo", "--branch", "main", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    policy = payload["would_put"]["deployment_branch_policy"]
    assert policy == {"protected_branches": False, "custom_branch_policies": True}
    assert payload["branch_policies"] == ["main"]


def test_env_dry_run_explicit_owner_skips_whoami(capsys, http_stub):
    rc = main(["repo", "env", "myrepo", "--owner", "agentculture", "--name", "testpypi", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "/repos/agentculture/myrepo/environments/testpypi" in payload["endpoint"]
    # No GET /user call needed when --owner is given.
    assert all(p != "/user" for _, p, _, _ in http_stub.calls)


def test_env_apply_puts_environment(capsys, http_stub):
    http_stub.set("GET", "/user", {"login": "octocat"})
    http_stub.set(
        "PUT",
        "/repos/octocat/myrepo/environments/pypi",
        {"name": "pypi", "id": 999, "url": "https://api.github.com/.../environments/pypi"},
    )
    rc = main(["repo", "env", "myrepo", "--apply", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is False
    assert payload["environment"]["name"] == "pypi"
    assert "settings/environments" in payload["environment_url"]


def test_env_apply_with_branch_creates_policy(capsys, http_stub):
    http_stub.set("GET", "/user", {"login": "octocat"})
    http_stub.set(
        "PUT",
        "/repos/octocat/myrepo/environments/pypi",
        {"name": "pypi", "id": 1},
    )
    http_stub.set(
        "POST",
        "/repos/octocat/myrepo/environments/pypi/deployment-branch-policies",
        {"name": "main", "id": 42},
    )
    rc = main(["repo", "env", "myrepo", "--branch", "main", "--apply", "--json"])
    assert rc == 0
    methods_paths = [(m, p) for m, p, _, _ in http_stub.calls]
    assert (
        "POST",
        "/repos/octocat/myrepo/environments/pypi/deployment-branch-policies",
    ) in methods_paths
