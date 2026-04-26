"""``ghafi whoami`` — verify the configured GitHub token via GET /user."""

from __future__ import annotations

import argparse

import ghafi._api as _api
from ghafi.cli._output import emit_json, emit_kv, emit_result


def cmd_whoami(args: argparse.Namespace) -> None:
    """Success path falls off the end (implicit None); errors raise GhafiError."""
    response = _api.http_request("GET", "/user")
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_json(response)
        return
    data = response or {}
    emit_result("**GitHub token**", json_mode=False)
    emit_kv(
        [
            ("login", data.get("login", "—")),
            ("id", data.get("id", "—")),
            ("type", data.get("type", "—")),
            ("name", data.get("name") or "—"),
        ]
    )


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "whoami",
        help="Verify the configured GITHUB_TOKEN against GET /user.",
    )
    p.add_argument("--json", action="store_true", help="Emit raw GitHub response.")
    p.set_defaults(func=cmd_whoami)
