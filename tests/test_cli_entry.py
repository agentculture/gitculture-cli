"""Top-level CLI entry — --version, no-args help, unknown verb."""

from __future__ import annotations

import json

import pytest

from gitculture import __version__
from gitculture.cli import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_no_args_prints_help_exit_zero(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "gitculture" in out
    assert "learn" in out


def test_unknown_subcommand_exits_user_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus"])
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Traceback" not in err


def test_unknown_subcommand_json_mode_emits_envelope(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus", "--json"])
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    payload = json.loads(err)
    assert payload["code"] == 1
