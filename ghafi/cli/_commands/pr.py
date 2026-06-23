"""``ghafi pr {list,approve}`` — find and approve pull requests.

Two verbs:

- ``list``    — read-only. Find open (or closed/all) PRs in an org, optionally
                narrowed to one ``--repo`` and/or filtered by ``--title``. Uses
                the GitHub Search API for org-wide scans (one request,
                paginated) and the per-repo pulls list when ``--repo`` is given.
- ``approve`` — submit an approving review (POST
                ``/repos/{owner}/{repo}/pulls/{number}/reviews`` with
                ``event=APPROVE``). Dry-run by default; ``--apply`` commits.

``pr list`` is the discovery half of the mass-approve workflow: an agent (or
the ``mass-approve-prs`` skill) lists matching PRs, reviews them, then calls
``pr approve`` per PR. Keeping the write verb single-PR and dry-run-default
preserves the mutation-safety contract (one reviewable mutation at a time).
"""

from __future__ import annotations

import argparse
import json as _json

import ghafi._api as _api
from ghafi.cli._errors import EXIT_API_ERROR, EXIT_USER_ERROR, GhafiError
from ghafi.cli._output import emit_json, emit_kv, emit_result, emit_table

# Title-match modes for `pr list --match`. All comparisons are
# case-insensitive and strip surrounding whitespace.
_MATCH_MODES = ("exact", "prefix", "substring")


def _title_matches(title: str, query: str, mode: str) -> bool:
    """Return True if ``title`` matches ``query`` under ``mode``.

    Case-insensitive, whitespace-stripped. ``exact`` requires equality,
    ``prefix`` requires the title to start with the query (heading
    semantics), ``substring`` requires containment.
    """
    t = (title or "").strip().lower()
    q = (query or "").strip().lower()
    if mode == "exact":
        return t == q
    if mode == "prefix":
        return t.startswith(q)
    return q in t


# --------------------------------------------------------------------------- #
# pr list
# --------------------------------------------------------------------------- #


def _split_owner_repo(repo_url: str) -> tuple[str, str]:
    """``https://api.github.com/repos/owner/name`` → ``(owner, name)``."""
    tail = repo_url.rsplit("/repos/", 1)[-1]
    parts = tail.split("/", 1)
    if len(parts) != 2:
        return "", tail
    return parts[0], parts[1]


def _list_via_repo(org: str, repo: str, state: str) -> list[dict]:
    """List PRs in one repo via ``/repos/{org}/{repo}/pulls`` (paginated)."""
    out: list[dict] = []
    page = 1
    while True:
        batch = _api.http_request(
            "GET",
            f"/repos/{org}/{repo}/pulls",
            query={"state": state, "per_page": 100, "page": page},
        )
        if not isinstance(batch, list) or not batch:
            break
        for pr in batch:
            out.append(
                {
                    "owner": org,
                    "repo": repo,
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "author": (pr.get("user") or {}).get("login", "?"),
                    "url": pr.get("html_url", ""),
                    "draft": bool(pr.get("draft", False)),
                }
            )
        if len(batch) < 100:
            break
        page += 1
    return out


def _build_search_query(org: str, state: str, title: str | None) -> str:
    parts = [f"org:{org}", "type:pr"]
    if state in ("open", "closed"):
        parts.append(f"state:{state}")
    if title:
        # Escape backslashes then quotes so an embedded `"` can't terminate the
        # in:title phrase early or inject extra Search qualifiers.
        escaped = title.strip().replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'in:title "{escaped}"')
    return " ".join(parts)


def _list_via_search(org: str, state: str, title: str | None) -> list[dict]:
    """Org-wide PR scan via the Search API (``/search/issues``, paginated)."""
    q = _build_search_query(org, state, title)
    out: list[dict] = []
    page = 1
    seen = 0
    while True:
        resp = _api.http_request(
            "GET",
            "/search/issues",
            query={"q": q, "per_page": 100, "page": page},
        )
        if not isinstance(resp, dict):
            break
        items = resp.get("items") or []
        total = int(resp.get("total_count", 0) or 0)
        for item in items:
            # Defensive: /search/issues mixes issues + PRs; keep only PRs.
            if "pull_request" not in item:
                continue
            owner, repo = _split_owner_repo(str(item.get("repository_url", "")))
            out.append(
                {
                    "owner": owner,
                    "repo": repo,
                    "number": item.get("number"),
                    "title": item.get("title", ""),
                    "author": (item.get("user") or {}).get("login", "?"),
                    "url": item.get("html_url", ""),
                    "draft": bool(item.get("draft", False)),
                }
            )
        seen += len(items)
        # Search API caps at 1000 results; stop on short page or exhaustion.
        if len(items) < 100 or seen >= total or seen >= 1000:
            break
        page += 1
    return out


def cmd_pr_list(args: argparse.Namespace) -> None:
    json_mode = bool(getattr(args, "json", False))
    if args.match not in _MATCH_MODES:
        raise GhafiError(
            code=EXIT_USER_ERROR,
            message=f"invalid --match {args.match!r}; expected one of {', '.join(_MATCH_MODES)}",
            remediation="pass --match exact|prefix|substring",
        )

    if args.repo:
        prs = _list_via_repo(args.org, args.repo, args.state)
    else:
        prs = _list_via_search(args.org, args.state, args.title)

    if args.title:
        prs = [p for p in prs if _title_matches(str(p["title"]), args.title, args.match)]
    prs.sort(key=lambda p: (str(p["repo"]), p["number"] or 0))

    if json_mode:
        emit_json(
            {
                "org": args.org,
                "repo": args.repo,
                "state": args.state,
                "title": args.title,
                "match": args.match,
                "count": len(prs),
                "pull_requests": prs,
            }
        )
        return

    scope = f"{args.org}/{args.repo}" if args.repo else args.org
    title_note = f" matching title ({args.match}) {args.title!r}" if args.title else ""
    emit_result(
        f"**{len(prs)} {args.state} PR(s) in {scope}{title_note}**\n",
        json_mode=False,
    )
    if prs:
        emit_table(
            headers=["repo", "#", "author", "title"],
            rows=[(p["repo"], p["number"], p["author"], p["title"]) for p in prs],
        )
    else:
        emit_result("_No matching pull requests._", json_mode=False)


# --------------------------------------------------------------------------- #
# pr approve
# --------------------------------------------------------------------------- #


def _resolve_owner_repo(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve ``(owner, repo)`` from the ``<repo>`` positional + ``--owner``.

    The positional may be ``owner/repo`` (split wins) or a bare repo name
    (then ``--owner`` is required — there is no whoami fallback for approvals,
    which are always against a specific upstream owner).
    """
    raw = str(args.repo)
    if "/" in raw:
        owner, _, name = raw.partition("/")
        if not owner or not name or "/" in name:
            raise GhafiError(
                code=EXIT_USER_ERROR,
                message=f"invalid repo {raw!r}: expected exactly one owner/repo",
                remediation=(
                    "use owner/repo (one slash, both parts non-empty), "
                    "or a bare name with --owner"
                ),
            )
        return owner, name
    if not args.owner:
        raise GhafiError(
            code=EXIT_USER_ERROR,
            message=f"cannot resolve owner for repo {raw!r}",
            remediation="pass --owner <login> or use the owner/repo form",
        )
    return str(args.owner), raw


def _approve_body(args: argparse.Namespace) -> dict[str, object]:
    body: dict[str, object] = {"event": "APPROVE"}
    if args.body:
        body["body"] = args.body
    return body


def cmd_pr_approve(args: argparse.Namespace) -> None:
    json_mode = bool(getattr(args, "json", False))
    owner, repo = _resolve_owner_repo(args)
    endpoint = f"/repos/{owner}/{repo}/pulls/{args.number}/reviews"
    body = _approve_body(args)

    if not args.apply:
        if json_mode:
            emit_json(
                {
                    "success": True,
                    "dry_run": True,
                    "endpoint": f"POST {endpoint}",
                    "would_post": body,
                }
            )
        else:
            emit_result("**Dry-run — no changes applied**\n", json_mode=False)
            emit_kv(
                [
                    ("endpoint", f"POST {endpoint}"),
                    ("pr", f"{owner}/{repo}#{args.number}"),
                    ("event", "APPROVE"),
                    ("body", args.body or "—"),
                ]
            )
            emit_result(
                "\n**would POST** body:\n```json\n" + _json.dumps(body, indent=2) + "\n```",
                json_mode=False,
            )
        return

    try:
        response = _api.http_request("POST", endpoint, payload=body) or {}
    except GhafiError as err:
        # You cannot approve your own PR (422). Surface it as a clear,
        # non-fatal-sounding error so a batch caller can skip and continue.
        if "your own pull request" in err.message.lower():
            raise GhafiError(
                code=EXIT_API_ERROR,
                message=f"cannot approve {owner}/{repo}#{args.number}: it is your own pull request",
                remediation="approve with a different account, or skip self-authored PRs",
            ) from None
        raise

    if json_mode:
        emit_json(
            {
                "success": True,
                "dry_run": False,
                "approved": f"{owner}/{repo}#{args.number}",
                "review_id": response.get("id"),
                "review_state": response.get("state"),
                "review_url": response.get("html_url"),
            }
        )
        return
    emit_result("**Pull request approved**\n", json_mode=False)
    emit_kv(
        [
            ("pr", f"{owner}/{repo}#{args.number}"),
            ("review state", response.get("state", "—")),
            ("review", response.get("html_url", "—")),
        ]
    )


# --------------------------------------------------------------------------- #
# pr merge
# --------------------------------------------------------------------------- #

_MERGE_METHODS = ("squash", "merge", "rebase")


def _merge_body(args: argparse.Namespace) -> dict[str, object]:
    body: dict[str, object] = {"merge_method": args.method}
    if args.commit_title:
        body["commit_title"] = args.commit_title
    if args.commit_message:
        body["commit_message"] = args.commit_message
    return body


def cmd_pr_merge(args: argparse.Namespace) -> None:
    json_mode = bool(getattr(args, "json", False))
    owner, repo = _resolve_owner_repo(args)
    endpoint = f"/repos/{owner}/{repo}/pulls/{args.number}/merge"
    body = _merge_body(args)

    if not args.apply:
        if json_mode:
            emit_json(
                {
                    "success": True,
                    "dry_run": True,
                    "endpoint": f"PUT {endpoint}",
                    "would_put": body,
                    "note": (
                        "Uses the direct merge endpoint — merges past non-required "
                        "failing checks (e.g. lint). Required-check bypass still "
                        "depends on branch protection allowing admins."
                    ),
                }
            )
        else:
            emit_result("**Dry-run — no changes applied**\n", json_mode=False)
            emit_kv(
                [
                    ("endpoint", f"PUT {endpoint}"),
                    ("pr", f"{owner}/{repo}#{args.number}"),
                    ("merge_method", args.method),
                ]
            )
            emit_result(
                "\n**would PUT** body:\n```json\n" + _json.dumps(body, indent=2) + "\n```",
                json_mode=False,
            )
            emit_result(
                "\n_Merges past non-required failing checks (e.g. lint); required-check "
                "bypass depends on branch protection allowing admins._",
                json_mode=False,
            )
        return

    try:
        response = _api.http_request("PUT", endpoint, payload=body) or {}
    except GhafiError as err:
        # 405 "not mergeable" is the branch-protection / required-check wall —
        # the direct endpoint cannot bypass required checks when protection
        # includes administrators. Surface it as a clear, skippable error.
        if "not mergeable" in err.message.lower() or "405" in err.message:
            raise GhafiError(
                code=EXIT_API_ERROR,
                message=f"cannot merge {owner}/{repo}#{args.number}: not mergeable",
                remediation=(
                    "the PR is not in a mergeable state — most often a merge "
                    "conflict (rebase/resolve against the base branch), or a "
                    "required status check / branch-protection rule an admin "
                    "merge cannot bypass"
                ),
            ) from None
        raise

    # A 200 response does not guarantee the merge happened — GitHub returns a
    # `merged` boolean. Treat merged != true as a failure so callers (and the
    # mass-merge skill, which counts on exit status) never over-count.
    if not response.get("merged", False):
        raise GhafiError(
            code=EXIT_API_ERROR,
            message=(
                f"GitHub did not merge {owner}/{repo}#{args.number}: "
                f"{response.get('message') or 'response reported merged=false'}"
            ),
            remediation="re-check the PR state — the merge did not complete",
        )

    if json_mode:
        emit_json(
            {
                "success": True,
                "dry_run": False,
                "merged": bool(response.get("merged", False)),
                "pr": f"{owner}/{repo}#{args.number}",
                "sha": response.get("sha"),
                "message": response.get("message"),
            }
        )
        return
    emit_result("**Pull request merged**\n", json_mode=False)
    emit_kv(
        [
            ("pr", f"{owner}/{repo}#{args.number}"),
            ("method", args.method),
            ("sha", response.get("sha", "—")),
            ("message", response.get("message", "—")),
        ]
    )


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def register(sub: "argparse._SubParsersAction") -> None:
    p = sub.add_parser("pr", help="Pull-request verbs (list, approve).")
    verbs = p.add_subparsers(dest="verb", required=True)

    ls = verbs.add_parser(
        "list",
        help="List/search PRs in an org (read-only). Filter by --title / --repo.",
    )
    ls.add_argument("org", help="Organization (or owner) login, e.g. agentculture.")
    ls.add_argument("--repo", help="Scope to one repo (lists its pulls directly).")
    ls.add_argument("--title", help="Filter to PRs whose title matches this text.")
    ls.add_argument(
        "--match",
        default="exact",
        choices=_MATCH_MODES,
        help="Title-match mode: exact (default), prefix (heading), or substring.",
    )
    ls.add_argument(
        "--state",
        default="open",
        choices=("open", "closed", "all"),
        help="PR state to include (default: open).",
    )
    ls.add_argument("--json", action="store_true", help="Emit a JSON envelope.")
    ls.set_defaults(func=cmd_pr_list)

    ap = verbs.add_parser(
        "approve",
        help="Approve a PR (dry-run by default; --apply submits the review).",
    )
    ap.add_argument("repo", help="Repository as owner/repo, or bare name with --owner.")
    ap.add_argument("number", type=int, help="Pull-request number.")
    ap.add_argument("--owner", help="Repository owner (when repo is a bare name).")
    ap.add_argument("--body", default="", help="Optional review comment body.")
    ap.add_argument("--apply", action="store_true", help="Actually POST (without it, dry-run).")
    ap.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    ap.set_defaults(func=cmd_pr_approve)

    mg = verbs.add_parser(
        "merge",
        help="Merge a PR via the direct endpoint (dry-run by default; --apply commits).",
    )
    mg.add_argument("repo", help="Repository as owner/repo, or bare name with --owner.")
    mg.add_argument("number", type=int, help="Pull-request number.")
    mg.add_argument("--owner", help="Repository owner (when repo is a bare name).")
    mg.add_argument(
        "--method",
        default="squash",
        choices=_MERGE_METHODS,
        help="Merge method: squash (default), merge, or rebase.",
    )
    mg.add_argument("--commit-title", default="", help="Override the merge commit title.")
    mg.add_argument("--commit-message", default="", help="Override the merge commit message.")
    mg.add_argument("--apply", action="store_true", help="Actually PUT (without it, dry-run).")
    mg.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    mg.set_defaults(func=cmd_pr_merge)
