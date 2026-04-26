"""Explain catalog — markdown keyed by command-path tuples."""

from __future__ import annotations

from ghafi.cli._errors import EXIT_USER_ERROR, GhafiError
from ghafi.explain.catalog import ENTRIES


def resolve(path: tuple[str, ...]) -> str:
    """Return the markdown body for ``path`` or raise :class:`GhafiError`."""
    if path in ENTRIES:
        return ENTRIES[path]
    display = " ".join(path) if path else "<root>"
    raise GhafiError(
        code=EXIT_USER_ERROR,
        message=f"no explain entry for: {display}",
        remediation="list known entries with: ghafi explain ghafi",
    )


def known_paths() -> list[tuple[str, ...]]:
    return list(ENTRIES.keys())
