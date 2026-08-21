#!/usr/bin/env bash
set -euo pipefail
cd /home/vosslab/nsh/vosslab-daily-blog
exec .venv/bin/python scripts/daily_publish.py "$@"
