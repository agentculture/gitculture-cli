#!/usr/bin/env bash
# mass-approve-prs.sh — find every open PR in an org whose title matches a
# heading and approve them in one pass, by composing two gitculture verbs:
#
#   gitculture pr list <org> --title <…> --match <…>   (read-only discovery)
#   gitculture pr approve <owner>/<repo> <number>      (one approving review each)
#
# Dry-run by default: it lists the matches and shows the approval each PR
# *would* get, then exits without writing. Re-run with --apply to actually
# submit the reviews. Per-PR failures (most commonly "you can't approve your
# own pull request", HTTP 422) are tallied as skipped/failed and never abort
# the batch. See ../SKILL.md for the why.
#
# Usage:
#   mass-approve-prs.sh --title "<heading>" [--org agentculture]
#       [--match exact|prefix|substring] [--state open|closed|all]
#       [--repo NAME] [--body "<review note>"] [--apply]
#
#   --title   TEXT   PR-title heading to match (required).
#   --org     ORG    Organization login (default: agentculture).
#   --match   MODE   Title match: exact (default), prefix (heading), substring.
#   --state   STATE  PR state to include (default: open).
#   --repo    NAME   Restrict to a single repo instead of scanning the org.
#   --body    TEXT   Review comment posted with each approval (signed default).
#   --apply          Actually submit the approvals (without it: dry-run).
#
# Requires: python3 (stdlib only) and gitculture (installed, or run from the
# ghafi checkout so `uv run gitculture` resolves). Auth: GITHUB_TOKEN or
# GH_TOKEN; the script bridges `gh auth token` when neither is set. Approving
# PRs needs the `repo` scope (classic) or fine-grained "Pull requests: write".
set -euo pipefail

ORG="agentculture"
TITLE=""
MATCH="exact"
STATE="open"
REPO=""
APPLY=""
BODY=$'Approved via gitculture `mass-approve-prs` skill.\n\n- Claude'

usage() { sed -n '2,30p' "$0"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2 ;;
    --org)   ORG="$2"; shift 2 ;;
    --match) MATCH="$2"; shift 2 ;;
    --state) STATE="$2"; shift 2 ;;
    --repo)  REPO="$2"; shift 2 ;;
    --body)  BODY="$2"; shift 2 ;;
    --apply) APPLY="--apply"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$TITLE" ]]; then
  echo "error: --title is required" >&2
  usage
  exit 2
fi

command -v python3 >/dev/null 2>&1 || { echo "error: python3 not found" >&2; exit 2; }

# Bridge gh auth → GITHUB_TOKEN if neither token var is set.
if [[ -z "${GITHUB_TOKEN:-}" && -z "${GH_TOKEN:-}" ]]; then
  if command -v gh >/dev/null 2>&1; then
    GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
    if [[ -n "$GITHUB_TOKEN" ]]; then
      export GITHUB_TOKEN
      echo "note: bridged GITHUB_TOKEN from \`gh auth token\`" >&2
    fi
  fi
fi

# Resolve the gitculture entry point: prefer an installed binary, else run from
# the checkout (four levels up: scripts → skill → skills → .claude → repo root).
REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
if command -v gitculture >/dev/null 2>&1; then
  GITCULTURE=(gitculture)
else
  GITCULTURE=(uv run --project "$REPO_ROOT" gitculture)
fi

echo "=== Plan ==="
echo "  org:     $ORG"
echo "  title:   $TITLE"
echo "  match:   $MATCH"
echo "  state:   $STATE"
echo "  repo:    ${REPO:-<all repos>}"
echo "  mode:    ${APPLY:+apply}${APPLY:-dry-run}"
echo

# --- discovery (read-only) --------------------------------------------------
list_args=(pr list "$ORG" --title "$TITLE" --match "$MATCH" --state "$STATE" --json)
[[ -n "$REPO" ]] && list_args+=(--repo "$REPO")

if ! list_json="$("${GITCULTURE[@]}" "${list_args[@]}")"; then
  echo "error: \`gitculture pr list\` failed (see above)" >&2
  exit 1
fi

# Parse JSON → TSV (owner, repo, number, author, title) via stdlib python3.
tsv="$(printf '%s' "$list_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for pr in data.get("pull_requests", []):
    fields = [
        str(pr.get("owner", "")),
        str(pr.get("repo", "")),
        str(pr.get("number", "")),
        str(pr.get("author", "")),
        str(pr.get("title", "")).replace("\t", " ").replace("\n", " "),
    ]
    print("\t".join(fields))
')"

if [[ -z "$tsv" ]]; then
  echo "No open PR(s) in $ORG match title ($MATCH): \"$TITLE\". Nothing to do."
  exit 0
fi

count="$(printf '%s\n' "$tsv" | grep -c '' || true)"
echo "=== Matched $count PR(s) ==="
printf '%s\n' "$tsv" | while IFS=$'\t' read -r owner repo number author title; do
  echo "  $owner/$repo#$number  ($author)  $title"
done
echo

# --- approve (or dry-run) ---------------------------------------------------
approved=0; skipped=0; failed=0
while IFS=$'\t' read -r owner repo number author title; do
  [[ -z "$number" ]] && continue
  echo "--- $owner/$repo#$number ---"
  approve_args=(pr approve "$owner/$repo" "$number" --body "$BODY")
  [[ -n "$APPLY" ]] && approve_args+=(--apply)

  if out="$("${GITCULTURE[@]}" "${approve_args[@]}" 2>&1)"; then
    echo "$out"
    [[ -n "$APPLY" ]] && approved=$((approved + 1))
  else
    echo "$out" >&2
    if printf '%s' "$out" | grep -qi 'your own pull request'; then
      echo "  (skipped: self-authored PR)" >&2
      skipped=$((skipped + 1))
    else
      echo "  (failed: see error above)" >&2
      failed=$((failed + 1))
    fi
  fi
done <<< "$tsv"

echo
echo "=== Summary ==="
if [[ -z "$APPLY" ]]; then
  echo "  matched:  $count  (dry-run — re-run with --apply to approve)"
else
  echo "  approved: $approved"
  echo "  skipped:  $skipped  (self-authored)"
  echo "  failed:   $failed"
fi

# Non-zero exit only when an apply run hit a non-skip failure.
[[ -n "$APPLY" && "$failed" -gt 0 ]] && exit 1
exit 0
