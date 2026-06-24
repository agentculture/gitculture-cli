"""``gitculture overview`` — org GitHub Actions minute-quota usage breakdown.

Read-only. Answers "why is the org near its included-minutes limit" by
joining the enhanced-billing usage report against each repo's
private/public flag and weighting by runner-OS multiplier.

Only PRIVATE repositories draw down the included-minutes quota (public
repos get unlimited free minutes), and the runner OS multiplies quota
cost: Linux x1, Windows x2, macOS x10. A small macOS matrix leg can
therefore outweigh a busy Linux repo — surfacing that is the whole point.

With ``--repo NAME`` it drills into one repo: workflow-run counts grouped
by workflow + trigger event (over the most recent 100 runs), plus the
total run count for the month.
"""

from __future__ import annotations

import argparse
import datetime

import gitculture._api as _api
from gitculture.cli._errors import EXIT_AUTH_ERROR, EXIT_USER_ERROR, GitcultureError
from gitculture.cli._output import emit_json, emit_kv, emit_result, emit_table

# GitHub Actions included-minutes multipliers by runner OS.
# https://docs.github.com/billing/managing-billing-for-github-actions
_WINDOWS_MULTIPLIER = 2
_MACOS_MULTIPLIER = 10
_LINUX_MULTIPLIER = 1


def _sku_multiplier(sku: str) -> int:
    """Map a billing SKU string to its included-minutes quota multiplier."""
    s = sku.lower()
    if "macos" in s:
        return _MACOS_MULTIPLIER
    if "windows" in s:
        return _WINDOWS_MULTIPLIER
    return _LINUX_MULTIPLIER


def _parse_month(month: str | None) -> tuple[int, int]:
    """Return ``(year, month_int)`` from a ``YYYY-MM`` string (default: now)."""
    if not month:
        today = datetime.date.today()
        return today.year, today.month
    try:
        year_s, mon_s = month.split("-", 1)
        year, mon = int(year_s), int(mon_s)
    except (ValueError, AttributeError):
        raise GitcultureError(
            code=EXIT_USER_ERROR,
            message=f"invalid --month {month!r}; expected YYYY-MM",
            remediation="pass a calendar month like --month 2026-06",
        ) from None
    if not (1 <= mon <= 12) or year < 2020:
        raise GitcultureError(
            code=EXIT_USER_ERROR,
            message=f"invalid --month {month!r}; expected YYYY-MM with month 1-12",
            remediation="pass a calendar month like --month 2026-06",
        )
    return year, mon


def _fetch_private_repos(org: str) -> set[str]:
    """Return the set of PRIVATE repo names in ``org`` (paginated)."""
    private: set[str] = set()
    page = 1
    while True:
        batch = _api.http_request(
            "GET",
            f"/orgs/{org}/repos",
            query={"per_page": 100, "page": page},
        )
        if not isinstance(batch, list) or not batch:
            break
        for repo in batch:
            if repo.get("private"):
                private.add(str(repo.get("name")))
        if len(batch) < 100:
            break
        page += 1
    return private


def _fetch_usage(org: str, year: int, mon: int) -> list[dict]:
    """Fetch the enhanced-billing usage items for ``org`` in the month."""
    try:
        report = _api.http_request(
            "GET",
            f"/organizations/{org}/settings/billing/usage",
            query={"year": year, "month": mon},
        )
    except GitcultureError as err:
        # The enhanced-billing endpoint needs admin:org (read:org is not
        # enough). Enrich the generic auth remediation with that specifics.
        if err.code == EXIT_AUTH_ERROR:
            raise GitcultureError(
                code=EXIT_AUTH_ERROR,
                message=err.message,
                remediation=(
                    "the org billing-usage endpoint needs the `admin:org` scope "
                    "(read:org alone returns 403). Refresh with "
                    "`gh auth refresh -h github.com -s admin:org` and export "
                    "GITHUB_TOKEN=$(gh auth token)"
                ),
            ) from None
        raise
    items = (report or {}).get("usageItems") if isinstance(report, dict) else None
    return items or []


def _aggregate(usage_items: list[dict], private: set[str]) -> dict:
    """Aggregate Actions minutes into per-private-repo weighted/raw totals."""
    weighted: dict[str, float] = {}
    raw: dict[str, float] = {}
    public_raw = 0.0
    for item in usage_items:
        if item.get("product") != "actions" or item.get("unitType") != "Minutes":
            continue
        repo = str(item.get("repositoryName", ""))
        qty = float(item.get("quantity", 0) or 0)
        if repo in private:
            mult = _sku_multiplier(str(item.get("sku", "")))
            weighted[repo] = weighted.get(repo, 0.0) + qty * mult
            raw[repo] = raw.get(repo, 0.0) + qty
        else:
            public_raw += qty
    rows = sorted(
        ({"repo": r, "weighted": round(weighted[r]), "raw": round(raw[r])} for r in weighted),
        key=lambda d: d["weighted"],
        reverse=True,
    )
    return {
        "repos": rows,
        "private_total_weighted": round(sum(weighted.values())),
        "private_total_raw": round(sum(raw.values())),
        "public_total_raw": round(public_raw),
    }


def _overview_org(args: argparse.Namespace, year: int, mon: int) -> None:
    json_mode = bool(getattr(args, "json", False))
    private = _fetch_private_repos(args.org)
    usage = _fetch_usage(args.org, year, mon)
    agg = _aggregate(usage, private)
    month_label = f"{year:04d}-{mon:02d}"

    if json_mode:
        emit_json({"org": args.org, "month": month_label, **agg})
        return

    emit_result(f"**GitHub Actions quota usage — {args.org} — {month_label}**\n", json_mode=False)
    emit_result(
        "_Only private repos draw down the quota. Weight: Linux ×1, " "Windows ×2, macOS ×10._\n",
        json_mode=False,
    )
    if agg["repos"]:
        emit_table(
            headers=["weighted", "raw", "repo"],
            rows=[(r["weighted"], r["raw"], r["repo"]) for r in agg["repos"]],
        )
    else:
        emit_result("_No private-repo Actions minutes recorded this month._", json_mode=False)
    emit_result("", json_mode=False)
    emit_kv(
        [
            ("private quota-weighted minutes", agg["private_total_weighted"]),
            ("private raw minutes", agg["private_total_raw"]),
            ("public raw minutes (free)", agg["public_total_raw"]),
        ]
    )
    if agg["repos"]:
        top = agg["repos"][0]["repo"]
        emit_result(
            f"\n_Drill into the top consumer: "
            f"`gitculture overview {args.org} --month {month_label} --repo {top}`_",
            json_mode=False,
        )


def _overview_repo(args: argparse.Namespace, year: int, mon: int) -> None:
    json_mode = bool(getattr(args, "json", False))
    month_label = f"{year:04d}-{mon:02d}"
    response = (
        _api.http_request(
            "GET",
            f"/repos/{args.org}/{args.repo}/actions/runs",
            query={"per_page": 100, "created": month_label},
        )
        or {}
    )
    total = response.get("total_count", 0) if isinstance(response, dict) else 0
    runs = response.get("workflow_runs", []) if isinstance(response, dict) else []

    counts: dict[tuple[str, str], int] = {}
    for run in runs:
        key = (str(run.get("name", "?")), str(run.get("event", "?")))
        counts[key] = counts.get(key, 0) + 1
    grouped = sorted(
        ({"count": c, "workflow": w, "event": e} for (w, e), c in counts.items()),
        key=lambda d: d["count"],
        reverse=True,
    )

    if json_mode:
        emit_json(
            {
                "org": args.org,
                "repo": args.repo,
                "month": month_label,
                "total_runs": total,
                "sampled_runs": len(runs),
                "by_workflow_event": grouped,
            }
        )
        return

    emit_result(f"**Workflow runs — {args.org}/{args.repo} — {month_label}**\n", json_mode=False)
    if grouped:
        emit_table(
            headers=["count", "workflow", "event"],
            rows=[(g["count"], g["workflow"], g["event"]) for g in grouped],
        )
    else:
        emit_result("_No workflow runs recorded this month._", json_mode=False)
    emit_result("", json_mode=False)
    emit_kv(
        [
            ("total runs this month", total),
            ("breakdown over most recent", f"{len(runs)} runs"),
        ]
    )


def cmd_overview(args: argparse.Namespace) -> None:
    """Success path falls off the end (implicit None); errors raise GitcultureError."""
    year, mon = _parse_month(getattr(args, "month", None))
    if getattr(args, "repo", None):
        _overview_repo(args, year, mon)
    else:
        _overview_org(args, year, mon)


def register(sub: "argparse._SubParsersAction") -> None:
    p = sub.add_parser(
        "overview",
        help="Org GitHub Actions minute-quota usage (read-only). --repo to drill in.",
    )
    p.add_argument("org", help="Organization login (e.g. agentculture).")
    p.add_argument(
        "--month",
        help="Billing month as YYYY-MM (default: current calendar month).",
    )
    p.add_argument(
        "--repo",
        help="Drill into one repo: run counts by workflow + trigger event.",
    )
    p.add_argument("--json", action="store_true", help="Emit a JSON envelope.")
    p.set_defaults(func=cmd_overview)
