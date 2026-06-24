"""gitculture whoami — auth probe; exit 2 / 3 / 0 paths."""

from __future__ import annotations

import json

from gitculture.cli import main
from gitculture.cli._errors import EXIT_AUTH_ERROR, EXIT_ENV_ERROR, GitcultureError


def test_whoami_text_emits_login(capsys, http_stub):
    http_stub.set(
        "GET", "/user", {"login": "octocat", "id": 1, "type": "User", "name": "The Octocat"}
    )
    rc = main(["whoami"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "octocat" in out
    assert "**login:** octocat" in out


def test_whoami_json_returns_raw_response(capsys, http_stub):
    payload = {"login": "octocat", "id": 1, "type": "User"}
    http_stub.set("GET", "/user", payload)
    rc = main(["whoami", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == payload


def test_whoami_no_token_exits_env_error(capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    rc = main(["whoami"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no GitHub token" in err


def test_whoami_401_exits_auth_error(capsys, http_stub):
    http_stub.set(
        "GET",
        "/user",
        GitcultureError(code=EXIT_AUTH_ERROR, message="GitHub API 401: Bad credentials"),
    )
    rc = main(["whoami"])
    err = capsys.readouterr().err
    assert rc == 3
    assert "401" in err


def test_whoami_gh_token_fallback(capsys, monkeypatch, http_stub):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_fallback")
    http_stub.set("GET", "/user", {"login": "fallback-user"})
    rc = main(["whoami"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "fallback-user" in out


# Reference EXIT_ENV_ERROR so flake8/isort don't strip the import.
_ = EXIT_ENV_ERROR
