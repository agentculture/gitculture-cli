"""Shared pytest fixtures — fixture-backed HTTP stub + env setup."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from ghafi import _api


class Stub:
    """Controllable replacement for ``ghafi._api.http_request``.

    - ``set(method, path, response_or_error)`` programs a keyed response.
    - ``queue(*items)`` stacks responses returned FIFO across calls.
    - ``stub.calls`` records ``(method, path, payload, query)`` tuples.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None, dict]] = []
        self._responses: dict[tuple[str, str], object] = {}
        self._queue: list[object] = []

    def set(self, method: str, path: str, response_or_error: object) -> None:
        self._responses[(method, path)] = response_or_error

    def queue(self, *items: object) -> None:
        self._queue.extend(items)

    def __call__(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        q = dict(query or {})
        self.calls.append((method, path, payload, q))
        if self._queue:
            item = self._queue.pop(0)
        else:
            key = (method, path)
            if key not in self._responses:
                raise AssertionError(f"unprogrammed call: {method} {path} query={q}")
            item = self._responses[key]
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def http_stub(monkeypatch):
    stub = Stub()
    monkeypatch.setattr(_api, "http_request", stub)
    return stub


@pytest.fixture(autouse=True)
def _default_env(monkeypatch):
    """Every CLI test gets a valid-looking GitHub token by default."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.delenv("GH_TOKEN", raising=False)


class AfiStub:
    """Controllable replacement for subprocess.run when invoking `afi`.

    Use as: ``afi_stub.program(stdout=..., stderr=..., returncode=...)``.
    """

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self._stdout = ""
        self._stderr = ""
        self._returncode = 0

    def program(self, *, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode

    def __call__(self, cmd, capture_output=True, text=True, check=False):
        self.calls.append(list(cmd))
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=self._returncode,
            stdout=self._stdout,
            stderr=self._stderr,
        )


@pytest.fixture
def afi_stub(monkeypatch):
    stub = AfiStub()
    # Make shutil.which("afi") return a fake path so _require_afi succeeds.
    monkeypatch.setattr(
        "ghafi.cli._commands.repo.shutil.which",
        lambda name: "/fake/bin/afi" if name == "afi" else None,
    )
    monkeypatch.setattr(
        "ghafi.cli._commands.repo.subprocess.run",
        stub,
    )
    return stub
