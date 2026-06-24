"""GitcultureError and exit-code policy.

Every failure inside gitculture raises :class:`GitcultureError`. The top-level
``main()`` catches it, formats via :mod:`gitculture.cli._output`, and exits
with :attr:`GitcultureError.code`. No Python traceback ever reaches stderr —
agents can parse our error shape reliably.
"""

from __future__ import annotations

from dataclasses import dataclass

# Exit-code policy.
# 0 = success
# 1 = user-input error (bad flag, missing required arg)
# 2 = environment / setup error (no GITHUB_TOKEN, missing afi binary, etc.)
# 3 = authentication error (401/403 from GitHub)
# 4 = upstream GitHub API error (non-2xx, network, or peer tool failure)
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_ENV_ERROR = 2
EXIT_AUTH_ERROR = 3
EXIT_API_ERROR = 4


@dataclass
class GitcultureError(Exception):
    """Structured error raised within gitculture; carries a remediation hint."""

    code: int
    message: str
    remediation: str = ""

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }
