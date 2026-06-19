#!/usr/bin/env bash
# actions-usage.sh — audit GitHub Actions minute consumption for an org and
# explain *why* the included-minutes quota is being drawn down.
#
# The included-minutes quota (3000/mo on the Team plan) is charged only for
# PRIVATE repositories; public repos get unlimited free minutes. Runner OS
# carries a quota multiplier: Linux x1, Windows x2, macOS x10. This script
# pulls the org's enhanced-billing usage for a month, joins it against each
# repo's private/public flag, and reports quota-weighted minutes per private
# repo so the real cost drivers surface (e.g. a small macOS matrix leg can
# outweigh a busy Linux repo).
#
# Usage:
#   actions-usage.sh [--org ORG] [--month YYYY-MM] [--repo NAME] [--json]
#
#   --org ORG        organization login (default: agentculture)
#   --month YYYY-MM  billing month, calendar (default: current month)
#   --repo NAME      drill into one repo: run counts by workflow + event
#   --json           emit the raw billing usageItems JSON and exit
#
# Requires: gh (authenticated), jq, awk.
# Token scope: the enhanced billing usage endpoint needs admin:org OR a
# fine-grained token with "Administration"/billing read. read:org alone is
# NOT enough. If you hit HTTP 403/410, run:
#   gh auth refresh -h github.com -s admin:org
#
# Quota multipliers reference:
#   https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions
set -euo pipefail

org="agentculture"
month="$(date +%Y-%m)"
repo=""
emit_json=0

while [ $# -gt 0 ]; do
  case "$1" in
    --org)   org="$2"; shift 2 ;;
    --month) month="$2"; shift 2 ;;
    --repo)  repo="$2"; shift 2 ;;
    --json)  emit_json=1; shift ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

for bin in gh jq awk; do
  command -v "$bin" >/dev/null 2>&1 || { echo "missing dependency: $bin" >&2; exit 2; }
done

year="${month%%-*}"
mon="${month##*-}"
mon="$((10#$mon))"   # strip leading zero for the API

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

usage_json="$workdir/usage.json"
if ! gh api "/organizations/${org}/settings/billing/usage?year=${year}&month=${mon}" \
      > "$usage_json" 2>"$workdir/err"; then
  echo "billing usage request failed:" >&2
  cat "$workdir/err" >&2
  echo "" >&2
  echo "The enhanced billing endpoint needs admin:org. Try:" >&2
  echo "  gh auth refresh -h github.com -s admin:org" >&2
  exit 1
fi

if [ "$emit_json" -eq 1 ]; then
  cat "$usage_json"
  exit 0
fi

# ---- drill-down mode -------------------------------------------------------
if [ -n "$repo" ]; then
  mm="$(printf '%02d' "$mon")"
  echo "=== ${org}/${repo}: workflows ==="
  gh api "/repos/${org}/${repo}/actions/workflows" \
    --jq '.workflows[] | "\(.state)\t\(.name)\t\(.path)"'
  echo ""
  echo "=== ${org}/${repo}: run count by workflow + event (${year}-${mm}, last 100) ==="
  gh api "/repos/${org}/${repo}/actions/runs?per_page=100&created=${year}-${mm}" \
    --jq '[.workflow_runs[] | {name, event}]
          | group_by(.name+"|"+.event)[]
          | "\(length)\t\(.[0].name)\t\(.[0].event)"' | sort -rn
  echo ""
  total=$(gh api "/repos/${org}/${repo}/actions/runs?per_page=1&created=${year}-${mm}" --jq '.total_count')
  echo "total runs in ${year}-${mm}: ${total}"
  exit 0
fi

# ---- org-wide breakdown ----------------------------------------------------
# repo privacy lookup
repos_meta="$workdir/repos.tsv"
gh api "/orgs/${org}/repos?per_page=100" --paginate \
  --jq '.[] | "\(.name)\t\(.private)"' > "$repos_meta"

# minute line items (Linux/Windows/macOS), quota-weighted by OS multiplier
min_tsv="$workdir/minutes.tsv"
jq -r '.usageItems[]
       | select(.product=="actions" and .unitType=="Minutes")
       | [.repositoryName, .sku, .quantity] | @tsv' "$usage_json" > "$min_tsv"

echo "=== ${org} — GitHub Actions quota usage for ${month} ==="
echo "(Only PRIVATE repos draw down the included-minutes quota."
echo " Quota weight: Linux x1, Windows x2, macOS x10.)"
echo ""

awk -F'\t' '
  FNR==NR { if($2=="true") priv[$1]=1; next }
  {
    repo=$1; sku=$2; q=$3
    mult=1
    if(sku ~ /Windows/) mult=2
    if(sku ~ /macOS/)   mult=10
    w=q*mult
    if(repo in priv){ wt[repo]+=w; raw[repo]+=q; privtot+=w; privraw+=q }
    else            { pubtot+=q }
  }
  END{
    printf "  weighted     raw  repo\n"
    printf "  --------  ------  --------------------\n"
    for(r in wt) printf "%10.0f %7.0f  %s\n", wt[r], raw[r], r | "sort -rn"
    close("sort -rn")
    printf "\n"
    printf "PRIVATE quota-weighted minutes (counts against quota): %.0f\n", privtot
    printf "PRIVATE raw minutes:                                   %.0f\n", privraw
    printf "PUBLIC raw minutes (free, unlimited):                  %.0f\n", pubtot
  }
' "$repos_meta" "$min_tsv"

echo ""
echo "Tip: drill into the top consumer with:"
echo "  $(basename "$0") --org ${org} --month ${month} --repo <name>"
