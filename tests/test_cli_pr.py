"""ghafi pr — list (search + repo modes, title matching) and approve."""

from __future__ import annotations

import json

from ghafi.cli import main
from ghafi.cli._errors import EXIT_API_ERROR, EXIT_USER_ERROR, GhafiError

ORG = "agentculture"
SEARCH_PATH = "/search/issues"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

TITLE = "Add eidetic remember/recall memory skills"


def _search_item(org: str, repo: str, number: int, title: str, author: str = "bot") -> dict:
    return {
        "number": number,
        "title": title,
        "html_url": f"https://github.com/{org}/{repo}/pull/{number}",
        "repository_url": f"https://api.github.com/repos/{org}/{repo}",
        "user": {"login": author},
        "pull_request": {"url": f"https://api.github.com/repos/{org}/{repo}/pulls/{number}"},
    }


# --------------------------------------------------------------------------- #
# pr list — search mode
# --------------------------------------------------------------------------- #


def test_pr_list_search_filters_by_exact_title(capsys, http_stub):
    http_stub.set(
        "GET",
        SEARCH_PATH,
        {
            "total_count": 3,
            "items": [
                _search_item(ORG, "katvan", 4, TITLE),
                _search_item(ORG, "colleague", 9, TITLE),
                # Fuzzy false positive the Search API might return — must be
                # filtered out by the client-side exact re-check.
                _search_item(ORG, "afi-cli", 2, "Add eidetic recall to the memory subsystem"),
            ],
        },
    )
    rc = main(["pr", "list", ORG, "--title", TITLE, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["count"] == 2
    # Sorted by (repo, number): colleague before katvan.
    assert [(p["repo"], p["number"]) for p in payload["pull_requests"]] == [
        ("colleague", 9),
        ("katvan", 4),
    ]
    assert payload["pull_requests"][0]["owner"] == ORG


def test_pr_list_is_read_only(http_stub):
    http_stub.set("GET", SEARCH_PATH, {"total_count": 0, "items": []})
    main(["pr", "list", ORG, "--title", TITLE])
    writes = [(m, p) for (m, p, _payload, _q) in http_stub.calls if m in WRITE_METHODS]
    assert writes == [], f"pr list leaked writes: {writes}"


def test_pr_list_search_query_includes_org_and_title(http_stub):
    http_stub.set("GET", SEARCH_PATH, {"total_count": 0, "items": []})
    main(["pr", "list", ORG, "--title", TITLE])
    # The single search call's query carries the org, type:pr, state, in:title.
    _method, _path, _payload, query = http_stub.calls[0]
    q = query["q"]
    assert f"org:{ORG}" in q
    assert "type:pr" in q
    assert "state:open" in q
    assert f'in:title "{TITLE}"' in q


def test_pr_list_prefix_match(capsys, http_stub):
    http_stub.set(
        "GET",
        SEARCH_PATH,
        {
            "total_count": 2,
            "items": [
                _search_item(ORG, "a", 1, f"{TITLE} (v2)"),
                _search_item(ORG, "b", 2, "Unrelated change"),
            ],
        },
    )
    rc = main(["pr", "list", ORG, "--title", TITLE, "--match", "prefix", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["count"] == 1
    assert payload["pull_requests"][0]["repo"] == "a"


def test_pr_list_text_table(capsys, http_stub):
    http_stub.set(
        "GET",
        SEARCH_PATH,
        {"total_count": 1, "items": [_search_item(ORG, "katvan", 4, TITLE, author="eidetic-bot")]},
    )
    rc = main(["pr", "list", ORG, "--title", TITLE])
    out = capsys.readouterr().out
    assert rc == 0
    assert "1 open PR(s)" in out
    assert "| katvan | 4 | eidetic-bot |" in out


# --------------------------------------------------------------------------- #
# pr list — repo mode
# --------------------------------------------------------------------------- #


def test_pr_list_repo_mode_uses_pulls_endpoint(capsys, http_stub):
    http_stub.set(
        "GET",
        f"/repos/{ORG}/katvan/pulls",
        [
            {
                "number": 4,
                "title": TITLE,
                "user": {"login": "bot"},
                "html_url": f"https://github.com/{ORG}/katvan/pull/4",
            },
            {
                "number": 5,
                "title": "Something else",
                "user": {"login": "bot"},
                "html_url": f"https://github.com/{ORG}/katvan/pull/5",
            },
        ],
    )
    rc = main(["pr", "list", ORG, "--repo", "katvan", "--title", TITLE, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["count"] == 1
    assert payload["pull_requests"][0]["number"] == 4
    # Must not have hit the search endpoint in repo mode.
    assert all(p != SEARCH_PATH for (_m, p, _pl, _q) in http_stub.calls)


# --------------------------------------------------------------------------- #
# pr approve
# --------------------------------------------------------------------------- #


def test_pr_approve_dry_run_prints_body_no_write(capsys, http_stub):
    rc = main(["pr", "approve", f"{ORG}/katvan", "4"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Dry-run" in out
    assert "APPROVE" in out
    writes = [(m, p) for (m, p, _payload, _q) in http_stub.calls if m in WRITE_METHODS]
    assert writes == [], f"dry-run leaked writes: {writes}"


def test_pr_approve_apply_posts_review(capsys, http_stub):
    http_stub.set(
        "POST",
        f"/repos/{ORG}/katvan/pulls/4/reviews",
        {"id": 999, "state": "APPROVED", "html_url": "https://github.com/x/y/pull/4#review-999"},
    )
    rc = main(["pr", "approve", f"{ORG}/katvan", "4", "--body", "lgtm", "--apply", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["approved"] == f"{ORG}/katvan#4"
    assert payload["review_state"] == "APPROVED"
    # Body carried event=APPROVE + the comment.
    method, path, sent, _q = http_stub.calls[-1]
    assert (method, path) == ("POST", f"/repos/{ORG}/katvan/pulls/4/reviews")
    assert sent == {"event": "APPROVE", "body": "lgtm"}


def test_pr_approve_owner_flag_form(http_stub):
    http_stub.set(
        "POST",
        f"/repos/{ORG}/katvan/pulls/4/reviews",
        {"id": 1, "state": "APPROVED"},
    )
    rc = main(["pr", "approve", "katvan", "4", "--owner", ORG, "--apply"])
    assert rc == 0
    assert http_stub.calls[-1][1] == f"/repos/{ORG}/katvan/pulls/4/reviews"


def test_pr_approve_bare_repo_without_owner_is_user_error(capsys):
    rc = main(["pr", "approve", "katvan", "4", "--apply"])
    err = capsys.readouterr().err
    assert rc == EXIT_USER_ERROR
    assert "cannot resolve owner" in err


def test_pr_approve_own_pr_maps_to_clear_error(capsys, http_stub):
    http_stub.set(
        "POST",
        f"/repos/{ORG}/katvan/pulls/4/reviews",
        GhafiError(
            code=EXIT_API_ERROR,
            message="GitHub API 422: Unprocessable Entity: Can not approve your own pull request",
        ),
    )
    rc = main(["pr", "approve", f"{ORG}/katvan", "4", "--apply"])
    err = capsys.readouterr().err
    assert rc == EXIT_API_ERROR
    assert "your own pull request" in err.lower()


# --------------------------------------------------------------------------- #
# pr merge
# --------------------------------------------------------------------------- #


def test_pr_merge_dry_run_prints_body_no_write(capsys, http_stub):
    rc = main(["pr", "merge", f"{ORG}/lobes-cli", "61"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Dry-run" in out
    assert '"merge_method": "squash"' in out
    writes = [(m, p) for (m, p, _payload, _q) in http_stub.calls if m in WRITE_METHODS]
    assert writes == [], f"dry-run leaked writes: {writes}"


def test_pr_merge_apply_puts_squash_merge(capsys, http_stub):
    http_stub.set(
        "PUT",
        f"/repos/{ORG}/lobes-cli/pulls/61/merge",
        {"sha": "3dba470", "merged": True, "message": "Pull Request successfully merged"},
    )
    rc = main(["pr", "merge", f"{ORG}/lobes-cli", "61", "--apply", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["merged"] is True
    assert payload["pr"] == f"{ORG}/lobes-cli#61"
    assert payload["sha"] == "3dba470"
    method, path, sent, _q = http_stub.calls[-1]
    assert (method, path) == ("PUT", f"/repos/{ORG}/lobes-cli/pulls/61/merge")
    assert sent == {"merge_method": "squash"}


def test_pr_merge_method_rebase(http_stub):
    http_stub.set(
        "PUT",
        f"/repos/{ORG}/lobes-cli/pulls/61/merge",
        {"sha": "abc", "merged": True},
    )
    rc = main(["pr", "merge", f"{ORG}/lobes-cli", "61", "--method", "rebase", "--apply"])
    assert rc == 0
    assert http_stub.calls[-1][2] == {"merge_method": "rebase"}


def test_pr_merge_not_mergeable_maps_to_clear_error(capsys, http_stub):
    http_stub.set(
        "PUT",
        f"/repos/{ORG}/lobes-cli/pulls/61/merge",
        GhafiError(code=EXIT_API_ERROR, message="GitHub API 405: Pull Request is not mergeable"),
    )
    rc = main(["pr", "merge", f"{ORG}/lobes-cli", "61", "--apply"])
    err = capsys.readouterr().err
    assert rc == EXIT_API_ERROR
    assert "not mergeable" in err.lower()
    # Remediation covers both common 405 causes: conflict and required-check.
    assert "conflict" in err.lower()
    assert "branch-protection" in err.lower()
