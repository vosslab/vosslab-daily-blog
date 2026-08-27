#!/usr/bin/env bash
# Process one completed Central-calendar day from mirror synchronization to editorial reconciliation.
set -euo pipefail

if [[ $# -ne 1 ]]; then
	printf 'Usage: %s YYYY-MM-DD\n' "$0" >&2
	exit 2
fi

REPORT_DATE="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLISH_WRAPPER="$HOME/.hermes/scripts/vosslab-daily-blog-publish.sh"

"$PUBLISH_WRAPPER" --date "$REPORT_DATE"
cd "$ROOT"
exec .venv/bin/python scripts/reconcile_editorial.py --date "$REPORT_DATE" --limit 1
