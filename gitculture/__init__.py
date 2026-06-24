"""gitculture — GitHub Agent First Interface."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

# The same code ships under two PyPI distribution names — "gitculture-cli"
# (canonical) and the legacy "ghafi" — so resolve whichever one is installed.
__version__ = "0.0.0+local"  # editable install before dist-info is built
for _dist in ("gitculture-cli", "ghafi"):
    try:
        __version__ = _pkg_version(_dist)
        break
    except PackageNotFoundError:
        continue
