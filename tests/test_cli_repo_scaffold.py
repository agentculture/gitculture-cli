"""gitculture repo scaffold — afi-missing, dry-run, apply, non-zero forwarding."""

from __future__ import annotations

import json

from gitculture.cli import main


def test_scaffold_afi_missing_exits_env_error(capsys, monkeypatch):
    monkeypatch.setattr(
        "gitculture.cli._commands.repo.shutil.which",
        lambda name: None,
    )
    rc = main(["repo", "scaffold", "."])
    err = capsys.readouterr().err
    assert rc == 2
    assert "afi binary not found" in err
    assert "pip install afi-cli" in err


def test_scaffold_dry_run_does_not_invoke_afi(capsys, afi_stub):
    rc = main(["repo", "scaffold", "/tmp/proj", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is True
    assert payload["would_run"][:3] == ["/fake/bin/afi", "cli", "cite"]
    assert afi_stub.calls == []


def test_scaffold_apply_forwards_afi_report(capsys, afi_stub):
    afi_report = {"out": "/tmp/proj/.afi/reference/python-cli", "written_count": 12}
    afi_stub.program(stdout=json.dumps(afi_report), stderr="", returncode=0)

    rc = main(["repo", "scaffold", "/tmp/proj", "--apply", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is False
    assert payload["afi_report"] == afi_report
    assert afi_stub.calls[0][:3] == ["/fake/bin/afi", "cli", "cite"]


def test_scaffold_apply_non_zero_exits_api_error(capsys, afi_stub):
    afi_stub.program(stdout="", stderr="afi: bad path", returncode=2)

    rc = main(["repo", "scaffold", "/bogus", "--apply"])
    captured = capsys.readouterr()
    assert rc == 4
    assert "afi cli cite exited 2" in captured.err
    assert "[afi] afi: bad path" in captured.err


def test_scaffold_apply_invalid_json_exits_api_error(capsys, afi_stub):
    afi_stub.program(stdout="not json", stderr="", returncode=0)
    rc = main(["repo", "scaffold", "/tmp/proj", "--apply"])
    err = capsys.readouterr().err
    assert rc == 4
    assert "not JSON" in err
