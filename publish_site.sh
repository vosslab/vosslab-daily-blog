#!/usr/bin/env bash
# Build current MkDocs source and atomically promote it to the LAN-served site.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! PYTHON_BIN="$(command -v python3.13)"; then
	echo "Python 3.13 publisher runtime is unavailable." >&2
	echo "Install Python 3.13 or activate a Python 3.13 virtual environment." >&2
	exit 1
fi

source "$SCRIPT_DIR/source_me.sh"
"$PYTHON_BIN" -m scripts.site_deployment

curl --fail --silent --show-error --output /dev/null http://127.0.0.1:8016/
curl --fail --silent --show-error --output /dev/null http://127.0.0.1:8016/status/

echo "Published and verified: http://aella.local:8016/"
