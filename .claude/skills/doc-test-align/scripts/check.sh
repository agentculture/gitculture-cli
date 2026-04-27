#!/usr/bin/env bash
# check.sh — v0 doc/test alignment checker. See ../SKILL.md.
#
# Compares CLAUDE.md claims to ghafi/ source code. Stub: only catches a
# narrow class of drift today. Extend cases as real failures surface.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$REPO_ROOT"

CLAUDE_MD="CLAUDE.md"
SRC_DIR="ghafi"

if [[ ! -f "$CLAUDE_MD" ]]; then
  echo "error: $CLAUDE_MD not found in $REPO_ROOT" >&2
  exit 2
fi

drift=0

echo "=== Check 1: endpoint prefixes in CLAUDE.md exist in $SRC_DIR/ ==="
# Pull each endpoint URL from CLAUDE.md, strip {placeholders}, then
# check that each non-empty static segment is referenced somewhere in
# ghafi/. Coarse but stable.
endpoints=$(grep -oE '/(repos|orgs|user)(/[A-Za-z0-9_{}/.:-]+)?' "$CLAUDE_MD" | sort -u)
if [[ -z "$endpoints" ]]; then
  echo "  (no endpoint mentions found in $CLAUDE_MD — nothing to check)"
else
  while IFS= read -r ep; do
    # Replace {placeholder} with a separator and extract static segments.
    cleaned=$(echo "$ep" | sed -E 's|\{[^}]+\}| |g')
    miss=()
    for seg in $cleaned; do
      seg_trim="${seg#/}"
      seg_trim="${seg_trim%/}"
      [[ -z "$seg_trim" ]] && continue
      if ! grep -RqF -- "$seg_trim" "$SRC_DIR/" 2>/dev/null; then
        miss+=("$seg_trim")
      fi
    done
    if [[ ${#miss[@]} -gt 0 ]]; then
      echo "  DRIFT: $CLAUDE_MD mentions '$ep' but these segments are absent from $SRC_DIR/: ${miss[*]}"
      drift=1
    fi
  done <<<"$endpoints"
  if [[ "$drift" -eq 0 ]]; then
    echo "  OK — every endpoint segment in $CLAUDE_MD has a code match"
  fi
fi
echo

echo "=== Check 2: bootstrap walkthrough verbs match registered verbs ==="
# Introspect the live parser instead of regex'ing source — robust to
# multi-line add_parser() calls. If introspection fails (uv missing,
# import error, etc.) exit 2 so the failure is actionable rather than
# masquerading as drift.
introspect_stderr=$(mktemp)
trap 'rm -f "$introspect_stderr"' EXIT
if ! registered=$(uv run python -c '
import argparse
from ghafi.cli import _build_parser
p = _build_parser()
sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
repo = sub.choices["repo"]
sub2 = next(a for a in repo._actions if isinstance(a, argparse._SubParsersAction))
print("\n".join(sorted(sub2.choices.keys())))
' 2>"$introspect_stderr"); then
  echo "  ERROR: parser introspection failed:" >&2
  sed 's/^/    /' "$introspect_stderr" >&2
  exit 2
fi
registered=$(echo "$registered" | sort -u)
mentioned=$(grep -oE 'ghafi repo [a-z]+' "$CLAUDE_MD" \
            | awk '{print $3}' | sort -u || true)
echo "  registered: $(echo "$registered" | tr '\n' ' ')"
echo "  mentioned:  $(echo "$mentioned" | tr '\n' ' ')"
for v in $mentioned; do
  if ! grep -qx "$v" <<<"$registered"; then
    echo "  DRIFT: $CLAUDE_MD references 'ghafi repo $v' but no such verb is registered"
    drift=1
  fi
done
echo

echo "=== Check 3: scope claims (informational only, v0) ==="
grep -nE '^- \`[a-z_:]+\` —' "$CLAUDE_MD" | sed 's/^/  /'
echo "  (v0: review the above by eye against the code; v1 should diff against _api annotations)"
echo

if [[ "$drift" -ne 0 ]]; then
  echo "DRIFT detected. Update $CLAUDE_MD or the code so they agree."
  exit 1
fi

echo "No drift detected."
