"""``ghafi repo {create,scaffold,env}`` — bootstrap a sibling repository.

Three verbs, all dry-run by default:

- ``create``  — POST /user/repos (or /orgs/{org}/repos), then PUT
                actions/permissions to enable workflows.
- ``scaffold`` — shell out to ``afi cli cite`` to render the python-cli
                template.
- ``env``     — PUT /repos/{owner}/{repo}/environments/{name} with a
                Trusted-Publishing-friendly shape (no secrets, no
                reviewers).
"""

from __future__ import annotations

import argparse
import json as _json
import shutil
import subprocess

import ghafi._api as _api
from ghafi.cli._errors import (
    EXIT_API_ERROR,
    EXIT_ENV_ERROR,
    EXIT_USER_ERROR,
    GhafiError,
)
from ghafi.cli._output import emit_diagnostic, emit_json, emit_kv, emit_result

# --------------------------------------------------------------------------- #
# repo create
# --------------------------------------------------------------------------- #


def _create_body(args: argparse.Namespace) -> dict[str, object]:
    body: dict[str, object] = {
        "name": args.name,
        "private": bool(args.private),
        "auto_init": True,
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
    }
    if args.description:
        body["description"] = args.description
    return body


def _create_endpoint(args: argparse.Namespace) -> str:
    if args.org:
        return f"/orgs/{args.org}/repos"
    return "/user/repos"


def _resolve_owner(args: argparse.Namespace) -> str:
    if args.org:
        return str(args.org)
    user = _api.http_request("GET", "/user") or {}
    login = user.get("login")
    if not login:
        raise GhafiError(
            code=EXIT_API_ERROR,
            message="GitHub /user response missing 'login'",
            remediation="check token validity with `ghafi whoami`",
        )
    return str(login)


def _set_actions_permissions(owner: str, name: str) -> None:
    _api.http_request(
        "PUT",
        f"/repos/{owner}/{name}/actions/permissions",
        payload={"enabled": True, "allowed_actions": "all"},
    )


def cmd_repo_create(args: argparse.Namespace) -> None:
    body = _create_body(args)
    endpoint = _create_endpoint(args)
    json_mode = bool(getattr(args, "json", False))

    if not args.apply:
        if json_mode:
            emit_json(
                {
                    "success": True,
                    "dry_run": True,
                    "endpoint": endpoint,
                    "would_post": body,
                }
            )
        else:
            emit_result("**Dry-run — no changes applied**\n", json_mode=False)
            emit_kv(
                [
                    ("endpoint", f"POST {endpoint}"),
                    ("name", args.name),
                    ("private", bool(args.private)),
                    ("description", args.description or "—"),
                ]
            )
            emit_result(
                "\n**would POST** body:\n```json\n" + _json.dumps(body, indent=2) + "\n```",
                json_mode=False,
            )
        return

    try:
        response = _api.http_request("POST", endpoint, payload=body)
    except GhafiError as err:
        # 422 with "name already exists" is idempotent: re-GET the repo.
        if err.code == EXIT_API_ERROR and "already exists" in err.message:
            owner = _resolve_owner(args)
            existing = _api.http_request("GET", f"/repos/{owner}/{args.name}") or {}
            if json_mode:
                emit_json(
                    {
                        "success": True,
                        "dry_run": False,
                        "already_existed": True,
                        "repo": existing,
                        "repo_url": existing.get("html_url"),
                    }
                )
                return
            emit_result("**Repository already exists** (no-op).\n", json_mode=False)
            emit_kv(
                [
                    ("repo", f"{owner}/{args.name}"),
                    ("url", existing.get("html_url", "—")),
                ]
            )
            return
        raise

    repo = response or {}
    owner = (repo.get("owner") or {}).get("login") or _resolve_owner(args)
    _set_actions_permissions(owner, args.name)

    if json_mode:
        emit_json(
            {
                "success": True,
                "dry_run": False,
                "created": repo,
                "repo_url": repo.get("html_url"),
                "actions_permissions_set": True,
            }
        )
        return
    emit_result("**Repository created**\n", json_mode=False)
    emit_kv(
        [
            ("repo", f"{owner}/{args.name}"),
            ("url", repo.get("html_url", "—")),
            ("private", repo.get("private", False)),
            ("actions", "enabled (allowed_actions=all)"),
        ]
    )


# --------------------------------------------------------------------------- #
# repo scaffold
# --------------------------------------------------------------------------- #


def _require_afi() -> str:
    afi_path = shutil.which("afi")
    if not afi_path:
        raise GhafiError(
            code=EXIT_ENV_ERROR,
            message="afi binary not found on PATH",
            remediation="install afi-cli: `pip install afi-cli` or `uv tool install afi-cli`",
        )
    return afi_path


def cmd_repo_scaffold(args: argparse.Namespace) -> None:
    afi_path = _require_afi()
    json_mode = bool(getattr(args, "json", False))

    if not args.apply:
        # afi has no native dry-run — running it writes files. So ghafi's
        # dry-run is descriptive only.
        cmd = [afi_path, "cli", "cite", args.path, "--lang", args.lang, "--json"]
        if json_mode:
            emit_json(
                {
                    "success": True,
                    "dry_run": True,
                    "would_run": cmd,
                    "note": (
                        "afi has no native dry-run; running it writes files. "
                        "Re-run with --apply to actually scaffold."
                    ),
                }
            )
        else:
            emit_result("**Dry-run — no changes applied**\n", json_mode=False)
            emit_kv(
                [
                    ("would run", " ".join(cmd)),
                    ("path", args.path),
                    ("lang", args.lang),
                ]
            )
            emit_result(
                "\n_afi has no native dry-run; re-run with `--apply` to scaffold._",
                json_mode=False,
            )
        return

    cmd = [afi_path, "cli", "cite", args.path, "--lang", args.lang, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603

    # Forward afi's stderr with a prefix so callers can distinguish it.
    if proc.stderr:
        for line in proc.stderr.splitlines():
            emit_diagnostic(f"[afi] {line}")

    if proc.returncode != 0:
        raise GhafiError(
            code=EXIT_API_ERROR,
            message=f"afi cli cite exited {proc.returncode}",
            remediation=(proc.stderr.strip() or "see [afi] diagnostics on stderr"),
        )

    try:
        afi_report = _json.loads(proc.stdout) if proc.stdout.strip() else {}
    except _json.JSONDecodeError as exc:
        raise GhafiError(
            code=EXIT_API_ERROR,
            message=f"afi cli cite stdout was not JSON: {exc}",
            remediation="re-run `afi cli cite <path> --lang python --json` directly to inspect",
        ) from None

    if json_mode:
        emit_json(
            {
                "success": True,
                "dry_run": False,
                "afi_report": afi_report,
            }
        )
        return
    emit_result("**Scaffold applied** (via afi cli cite)\n", json_mode=False)
    out_dir = afi_report.get("out") or afi_report.get("output_dir") or "—"
    written = afi_report.get("written") or afi_report.get("written_count") or "—"
    emit_kv(
        [
            ("path", args.path),
            ("lang", args.lang),
            ("out", out_dir),
            ("files written", written),
        ]
    )


# --------------------------------------------------------------------------- #
# repo env
# --------------------------------------------------------------------------- #


def _env_body(args: argparse.Namespace) -> dict[str, object]:
    if args.branch:
        policy: dict[str, object] | None = {
            "protected_branches": False,
            "custom_branch_policies": True,
        }
    else:
        policy = None
    return {
        "wait_timer": 0,
        "reviewers": None,
        "deployment_branch_policy": policy,
    }


def _env_branch_policies(args: argparse.Namespace) -> list[str]:
    if not args.branch:
        return []
    return [str(args.branch)]


def cmd_repo_env(args: argparse.Namespace) -> None:
    owner = args.owner or _resolve_owner_for_env()
    body = _env_body(args)
    endpoint = f"/repos/{owner}/{args.repo}/environments/{args.name}"
    json_mode = bool(getattr(args, "json", False))

    if not args.apply:
        if json_mode:
            emit_json(
                {
                    "success": True,
                    "dry_run": True,
                    "endpoint": f"PUT {endpoint}",
                    "would_put": body,
                    "branch_policies": _env_branch_policies(args),
                    "note": (
                        "Trusted Publishing uses OIDC; this environment stores no "
                        "secrets. Register the publisher on pypi.org separately: "
                        "https://docs.pypi.org/trusted-publishers/"
                    ),
                }
            )
        else:
            emit_result("**Dry-run — no changes applied**\n", json_mode=False)
            emit_kv(
                [
                    ("endpoint", f"PUT {endpoint}"),
                    ("environment", args.name),
                    ("branch", args.branch or "any"),
                ]
            )
            emit_result(
                "\n**would PUT** body:\n```json\n" + _json.dumps(body, indent=2) + "\n```",
                json_mode=False,
            )
            emit_result(
                "\n_PyPI side: register the trusted publisher at_ "
                "https://docs.pypi.org/trusted-publishers/",
                json_mode=False,
            )
        return

    response = _api.http_request("PUT", endpoint, payload=body) or {}
    # Optionally write branch policies (only meaningful when policy is custom).
    if args.branch:
        try:
            _api.http_request(
                "POST",
                f"/repos/{owner}/{args.repo}/environments/{args.name}"
                "/deployment-branch-policies",
                payload={"name": args.branch},
            )
        except GhafiError as err:
            # Branch-policy creation is best-effort; surface a diagnostic
            # but don't fail the env creation.
            emit_diagnostic(f"branch-policy create failed: {err.message}")

    if json_mode:
        emit_json(
            {
                "success": True,
                "dry_run": False,
                "environment": response,
                "environment_url": (
                    f"https://github.com/{owner}/{args.repo}/settings/environments"
                ),
            }
        )
        return
    emit_result("**Environment created** (Trusted Publishing)\n", json_mode=False)
    emit_kv(
        [
            ("repo", f"{owner}/{args.repo}"),
            ("environment", args.name),
            ("branch", args.branch or "any"),
            (
                "settings",
                f"https://github.com/{owner}/{args.repo}/settings/environments",
            ),
        ]
    )
    emit_result(
        "\n_Next: register the trusted publisher on pypi.org "
        "(https://docs.pypi.org/trusted-publishers/)._",
        json_mode=False,
    )


def _resolve_owner_for_env() -> str:
    user = _api.http_request("GET", "/user") or {}
    login = user.get("login")
    if not login:
        raise GhafiError(
            code=EXIT_USER_ERROR,
            message="--owner not given and GET /user has no 'login'",
            remediation="pass --owner <login>",
        )
    return str(login)


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def register(sub: "argparse._SubParsersAction") -> None:
    p = sub.add_parser("repo", help="Repository bootstrap (create, scaffold, env).")
    verbs = p.add_subparsers(dest="verb", required=True)

    c = verbs.add_parser(
        "create",
        help="Create a GitHub repository (dry-run by default; --apply commits).",
    )
    c.add_argument("name", help="Repository name (no slash; owner is implied).")
    c.add_argument("--org", help="Create under this organization instead of the auth user.")
    c.add_argument("--private", action="store_true", help="Make the repo private.")
    c.add_argument("--description", default="", help="Short description (optional).")
    c.add_argument("--apply", action="store_true", help="Actually POST (without it, dry-run).")
    c.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    c.set_defaults(func=cmd_repo_create)

    s = verbs.add_parser(
        "scaffold",
        help="Render the afi-cli template into a path (shells out to `afi`).",
    )
    s.add_argument("path", help="Target project directory.")
    s.add_argument(
        "--lang", default="python", help="Reference language (afi v0.4 supports python)."
    )
    s.add_argument(
        "--apply", action="store_true", help="Actually invoke afi (without it, dry-run)."
    )
    s.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    s.set_defaults(func=cmd_repo_scaffold)

    e = verbs.add_parser(
        "env",
        help="Create a Trusted-Publishing GitHub Environment (pypi/testpypi).",
    )
    e.add_argument("repo", help="Repository name (owner inferred from --owner or whoami).")
    e.add_argument("--owner", help="Repository owner; defaults to the authenticated user.")
    e.add_argument(
        "--name",
        default="pypi",
        help="Environment name (default: pypi). Pass --name testpypi for the test environment.",
    )
    e.add_argument(
        "--branch",
        help="Restrict deployments to this branch pattern (e.g. main). Default: any branch.",
    )
    e.add_argument("--apply", action="store_true", help="Actually PUT (without it, dry-run).")
    e.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    e.set_defaults(func=cmd_repo_env)
