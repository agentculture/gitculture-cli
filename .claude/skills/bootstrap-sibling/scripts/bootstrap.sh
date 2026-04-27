#!/usr/bin/env bash
# bootstrap.sh — chain `ghafi repo {create,scaffold,env}` to stand up a
# new AgentCulture sibling end-to-end. Dry-run by default; --apply to
# commit. See ../SKILL.md for rationale.

set -euo pipefail

ORG="agentculture"
NAME=""
DESCRIPTION=""
PRIVATE=""
APPLY=""

usage() {
  cat <<'EOF'
Usage:
  bootstrap.sh --name <repo> --description "<…>" [--org agentculture] [--private] [--apply]

Without --apply, every ghafi step prints its dry-run output and the
script exits before performing any mutation. With --apply, the script
performs all four mutations in order, with a confirmation prompt after
the dry-run review.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --description) DESCRIPTION="$2"; shift 2 ;;
    --org) ORG="$2"; shift 2 ;;
    --private) PRIVATE="--private"; shift ;;
    --apply) APPLY="--apply"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$NAME" || -z "$DESCRIPTION" ]]; then
  echo "error: --name and --description are required" >&2
  usage
  exit 2
fi

# Bridge gh auth → GITHUB_TOKEN if not already set.
if [[ -z "${GITHUB_TOKEN:-}" && -z "${GH_TOKEN:-}" ]]; then
  if command -v gh >/dev/null 2>&1; then
    GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
    if [[ -n "$GITHUB_TOKEN" ]]; then
      export GITHUB_TOKEN
      echo "note: bridged GITHUB_TOKEN from \`gh auth token\`"
    fi
  fi
fi

GHAFI=(uv run ghafi)
TARGET="$(cd "$(dirname "$0")/../../../.." && pwd)/$NAME"

echo "=== Plan ==="
echo "  org:           $ORG"
echo "  name:          $NAME"
echo "  description:   $DESCRIPTION"
echo "  private:       ${PRIVATE:-false}"
echo "  local target:  $TARGET"
echo "  mode:          ${APPLY:-dry-run}"
echo

# Step 1: repo create (always dry-run first; --apply if requested)
echo "=== Step 1: repo create (dry-run preview) ==="
"${GHAFI[@]}" repo create --org "$ORG" --description "$DESCRIPTION" $PRIVATE "$NAME"
echo

# Step 4 + 5 dry-run preview (envs)
echo "=== Step 4: repo env pypi (dry-run preview) ==="
"${GHAFI[@]}" repo env --owner "$ORG" --name pypi --branch main "$NAME"
echo
echo "=== Step 5: repo env testpypi (dry-run preview) ==="
"${GHAFI[@]}" repo env --owner "$ORG" --name testpypi "$NAME"
echo

if [[ -z "$APPLY" ]]; then
  echo "Dry-run complete. Re-run with --apply to commit."
  exit 0
fi

# Confirmation gate before applying.
read -r -p "Apply all four mutations? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

echo
echo "=== Step 1: repo create --apply ==="
"${GHAFI[@]}" repo create --org "$ORG" --description "$DESCRIPTION" $PRIVATE "$NAME" --apply

echo
echo "=== Step 2: git clone $ORG/$NAME → $TARGET ==="
git clone "https://github.com/$ORG/$NAME.git" "$TARGET"

echo
echo "=== Step 3: repo scaffold --apply ==="
"${GHAFI[@]}" repo scaffold --apply "$TARGET"

echo
echo "=== Step 4: repo env pypi --apply ==="
"${GHAFI[@]}" repo env --owner "$ORG" --name pypi --branch main --apply "$NAME"

echo
echo "=== Step 5: repo env testpypi --apply ==="
"${GHAFI[@]}" repo env --owner "$ORG" --name testpypi --apply "$NAME"

cat <<EOF

=== Manual follow-up (web only) ===
1. https://pypi.org/manage/account/publishing/      → register publisher
2. https://test.pypi.org/manage/account/publishing/ → register publisher

   Repository:    $ORG/$NAME
   Workflow:      publish.yml
   Environment:   pypi (and testpypi on the test side)

3. Instantiate .afi/reference/python-cli/{{slug}}/ into the actual package
   (afi-cli does not currently auto-instantiate; do this by hand or with a
   future afi verb).
4. Author publish.yml + tests.yml workflows in $TARGET/.github/workflows/.
EOF
