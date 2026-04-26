"""Allow ``python -m ghafi`` to invoke the CLI."""

from ghafi.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
