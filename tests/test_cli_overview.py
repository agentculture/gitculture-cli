"""gitculture overview — Actions quota breakdown; org table, drill-down, errors."""

from __future__ import annotations

import json

from gitculture.cli import main
from gitculture.cli._errors import EXIT_AUTH_ERROR, EXIT_USER_ERROR, GitcultureError

ORG = "agentculture"
REPOS_PATH = f"/orgs/{ORG}/repos"
USAGE_PATH = f"/organizations/{ORG}/settings/billing/usage"

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _program_org(http_stub):
    """Two private repos (one Linux-heavy, one macOS) + one public repo."""
    http_stub.set(
        "GET",
        REPOS_PATH,
        [
            {"name": "colleague", "private": True},
            {"name": "katvan", "private": True},
            {"name": "auntiepypi", "private": False},
        ],
    )
    http_stub.set(
        "GET",
        USAGE_PATH,
        {
            "usageItems": [
                _item("Actions Linux", 100, "colleague"),
                _item("Actions macOS 3-core", 5, "katvan"),
                # Public repo: large but must be excluded from quota.
                _item("Actions Linux", 9999, "auntiepypi"),
                # Storage line: not minutes, must be ignored.
                {
                    "product": "actions",
                    "unitType": "GigabyteHours",
                    "sku": "Actions storage",
                    "quantity": 3,
                    "repositoryName": "colleague",
                },
            ]
        },
    )


def _item(sku: str, qty: float, repo: str) -> dict:
    return {
        "product": "actions",
        "unitType": "Minutes",
        "sku": sku,
        "quantity": qty,
        "repositoryName": repo,
    }


def test_overview_text_table_and_totals(capsys, http_stub):
    _program_org(http_stub)
    rc = main(["overview", ORG, "--month", "2026-06"])
    out = capsys.readouterr().out
    assert rc == 0
    # macOS leg is weighted x10: 5 raw -> 50 weighted, so katvan ranks above
    # its raw minutes; colleague Linux 100 stays 100.
    assert "| 100 | 100 | colleague |" in out
    assert "| 50 | 5 | katvan |" in out
    # Totals: weighted 150, raw 105, public 9999 (free, excluded from quota).
    assert "**private quota-weighted minutes:** 150" in out
    assert "**private raw minutes:** 105" in out
    assert "**public raw minutes (free):** 9999" in out


def test_overview_json_envelope(capsys, http_stub):
    _program_org(http_stub)
    rc = main(["overview", ORG, "--month", "2026-06", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["org"] == ORG
    assert payload["month"] == "2026-06"
    assert payload["private_total_weighted"] == 150
    assert payload["private_total_raw"] == 105
    assert payload["public_total_raw"] == 9999
    # Sorted by weighted desc: colleague (100) before katvan (50).
    assert [r["repo"] for r in payload["repos"]] == ["colleague", "katvan"]
    assert payload["repos"][1] == {"repo": "katvan", "weighted": 50, "raw": 5}


def test_overview_is_read_only(http_stub):
    """overview must never issue a write, regardless of mode."""
    _program_org(http_stub)
    main(["overview", ORG])
    writes = [(m, p) for (m, p, _payload, _q) in http_stub.calls if m in WRITE_METHODS]
    assert writes == [], f"overview leaked writes: {writes}"


def test_overview_repo_drilldown(capsys, http_stub):
    http_stub.set(
        "GET",
        f"/repos/{ORG}/colleague/actions/runs",
        {
            "total_count": 615,
            "workflow_runs": [
                {"name": "Tests", "event": "push"},
                {"name": "Tests", "event": "pull_request"},
                {"name": "Tests", "event": "pull_request"},
                {"name": "Publish to PyPI", "event": "push"},
            ],
        },
    )
    rc = main(["overview", ORG, "--repo", "colleague", "--month", "2026-06", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["total_runs"] == 615
    assert payload["sampled_runs"] == 4
    # Tests/pull_request is the most frequent (2).
    assert payload["by_workflow_event"][0] == {
        "count": 2,
        "workflow": "Tests",
        "event": "pull_request",
    }


def test_overview_bad_month_user_error(capsys):
    rc = main(["overview", ORG, "--month", "2026-13"])
    err = capsys.readouterr().err
    assert rc == EXIT_USER_ERROR
    assert "invalid --month" in err


def test_overview_billing_403_enriches_admin_org_hint(capsys, http_stub):
    http_stub.set("GET", REPOS_PATH, [{"name": "x", "private": True}])
    http_stub.set(
        "GET",
        USAGE_PATH,
        GitcultureError(code=EXIT_AUTH_ERROR, message="GitHub API 403: Resource not accessible"),
    )
    rc = main(["overview", ORG])
    err = capsys.readouterr().err
    assert rc == EXIT_AUTH_ERROR
    assert "admin:org" in err
