"""HTTP helper for the GitHub REST API.

Stdlib only (urllib + json). Mirrors cfafi's _api.py shape — single
``http_request`` entry, raising :class:`GitcultureError` on 4xx/5xx with
401/403 mapped to EXIT_AUTH_ERROR and everything else to EXIT_API_ERROR.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, NoReturn

from gitculture import __version__
from gitculture._env import require_github_token
from gitculture.cli._errors import EXIT_API_ERROR, EXIT_AUTH_ERROR, GitcultureError

GITHUB_API_BASE = "https://api.github.com"


def http_request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Perform one GitHub API request, returning the parsed JSON body.

    Returns ``None`` for 204 No Content. Raises :class:`GitcultureError` on
    HTTP 4xx/5xx with 401/403 mapped to ``EXIT_AUTH_ERROR``, all other
    non-2xx mapped to ``EXIT_API_ERROR``. The GitHub error envelope
    (``message``) is preserved in the raised error.
    """
    token = require_github_token()
    url = GITHUB_API_BASE + path
    if query:
        url = f"{url}?{urllib.parse.urlencode({k: str(v) for k, v in query.items()})}"

    body: bytes | None = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"gitculture/{__version__} (github.com/agentculture/gitculture-cli)",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(
            req
        ) as resp:  # noqa: S310  # nosec B310 - bounded to GITHUB_API_BASE
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        _raise_http_error(exc)
    except urllib.error.URLError as exc:
        raise GitcultureError(
            code=EXIT_API_ERROR,
            message=f"GitHub API transport failure: {exc.reason}",
            remediation="check network connectivity and api.github.com reachability",
        ) from None


def _raise_http_error(exc: urllib.error.HTTPError) -> NoReturn:
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"message": raw or exc.reason}
    msg = data.get("message") or exc.reason or f"HTTP {exc.code}"
    code_category = EXIT_AUTH_ERROR if exc.code in (401, 403) else EXIT_API_ERROR
    remediation = (
        "verify your GITHUB_TOKEN scopes (need `repo` for repo create, "
        "`admin:repo_hook` for environments and Actions permissions, "
        "and `admin:org` for org repos)"
        if code_category == EXIT_AUTH_ERROR
        else f"HTTP {exc.code} from GitHub: {data.get('documentation_url', 'no docs URL')}"
    )
    # Surface validation errors verbatim so the agent can react.
    errors = data.get("errors")
    if errors:
        msg = f"{msg}: {json.dumps(errors)}"
    raise GitcultureError(
        code=code_category,
        message=f"GitHub API {exc.code}: {msg}",
        remediation=remediation,
    ) from None
