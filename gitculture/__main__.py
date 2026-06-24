"""Allow ``python -m gitculture`` to invoke the CLI."""

from gitculture.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
