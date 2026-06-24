"""Explain catalog — markdown keyed by command-path tuples."""

from __future__ import annotations

from gitculture.cli._errors import EXIT_USER_ERROR, GitcultureError
from gitculture.explain.catalog import ENTRIES


def resolve(path: tuple[str, ...]) -> str:
    """Return the markdown body for ``path`` or raise :class:`GitcultureError`."""
    if path in ENTRIES:
        return ENTRIES[path]
    display = " ".join(path) if path else "<root>"
    raise GitcultureError(
        code=EXIT_USER_ERROR,
        message=f"no explain entry for: {display}",
        remediation="list known entries with: gitculture explain gitculture",
    )


def known_paths() -> list[tuple[str, ...]]:
    return list(ENTRIES.keys())
