"""gitculture repo create — dry-run, --apply, --org, idempotency."""

from __future__ import annotations

import json

from gitculture.cli import main
from gitculture.cli._errors import EXIT_API_ERROR, GitcultureError


def test_repo_create_dry_run_text_shows_body(capsys, http_stub):
    rc = main(["repo", "create", "myrepo"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Dry-run" in out
    assert "POST /user/repos" in out
    assert '"name": "myrepo"' in out
    # No HTTP call should have been made in dry-run.
    assert http_stub.calls == []


def test_repo_create_dry_run_json_envelope(capsys, http_stub):
    rc = main(["repo", "create", "myrepo", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is True
    assert payload["endpoint"] == "/user/repos"
    assert payload["would_post"]["name"] == "myrepo"
    assert payload["would_post"]["auto_init"] is True
    assert payload["would_post"]["has_wiki"] is False


def test_repo_create_org_uses_org_endpoint(capsys, http_stub):
    rc = main(["repo", "create", "myrepo", "--org", "agentculture", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["endpoint"] == "/orgs/agentculture/repos"


def test_repo_create_apply_posts_and_sets_permissions(capsys, http_stub):
    http_stub.set(
        "POST",
        "/user/repos",
        {
            "name": "myrepo",
            "html_url": "https://github.com/octocat/myrepo",
            "owner": {"login": "octocat"},
            "private": False,
        },
    )
    http_stub.set("PUT", "/repos/octocat/myrepo/actions/permissions", None)

    rc = main(["repo", "create", "myrepo", "--apply", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is False
    assert payload["actions_permissions_set"] is True
    assert payload["repo_url"] == "https://github.com/octocat/myrepo"

    methods_paths = [(m, p) for m, p, _, _ in http_stub.calls]
    assert ("POST", "/user/repos") in methods_paths
    assert ("PUT", "/repos/octocat/myrepo/actions/permissions") in methods_paths


def test_repo_create_idempotent_on_422_already_exists(capsys, http_stub):
    http_stub.set(
        "POST",
        "/user/repos",
        GitcultureError(
            code=EXIT_API_ERROR, message="GitHub API 422: name already exists on this account"
        ),
    )
    http_stub.set("GET", "/user", {"login": "octocat"})
    http_stub.set(
        "GET",
        "/repos/octocat/myrepo",
        {"name": "myrepo", "html_url": "https://github.com/octocat/myrepo"},
    )

    rc = main(["repo", "create", "myrepo", "--apply", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["already_existed"] is True
    assert payload["repo_url"] == "https://github.com/octocat/myrepo"
