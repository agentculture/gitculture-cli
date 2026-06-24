"""gitculture explain — known paths resolve, unknown paths exit non-zero."""

from __future__ import annotations

import json

from gitculture.cli import main


def test_explain_root_resolves(capsys):
    rc = main(["explain"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "gitculture" in out


def test_explain_repo_create_resolves(capsys):
    rc = main(["explain", "repo", "create"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "gitculture repo create" in out
    assert "--apply" in out


def test_explain_unknown_path_exits_user_error(capsys):
    rc = main(["explain", "nope"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "no explain entry" in err
    assert "hint:" in err
    # No Python traceback leaks.
    assert "Traceback" not in err


def test_explain_json_mode_envelope(capsys):
    rc = main(["explain", "repo", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["path"] == ["repo"]
    assert "gitculture repo" in payload["markdown"]


def test_explain_unknown_json_mode_emits_error_envelope(capsys):
    rc = main(["explain", "nope", "--json"])
    err = capsys.readouterr().err
    payload = json.loads(err)
    assert rc == 1
    assert payload["code"] == 1
    assert "no explain entry" in payload["message"]
