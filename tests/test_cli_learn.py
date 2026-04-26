"""ghafi learn — text and JSON modes both work."""

from __future__ import annotations

import json

from ghafi.cli import main


def test_learn_text_mentions_required_topics(capsys):
    rc = main(["learn"])
    out = capsys.readouterr().out
    assert rc == 0
    # Rubric bundle 2: ≥200 chars + mentions purpose, commands, exit codes,
    # --json, and explain.
    assert len(out) >= 200
    assert "Purpose" in out
    assert "Commands" in out
    assert "Exit-code policy" in out
    assert "--json" in out
    assert "explain" in out


def test_learn_json_carries_required_keys(capsys):
    rc = main(["learn", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    for key in ("tool", "version", "purpose", "commands", "exit_codes", "json_support"):
        assert key in payload, key
    assert payload["tool"] == "ghafi"
    assert payload["json_support"] is True
