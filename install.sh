#!/bin/bash
# One-time setup: local venv + Playwright + Firefox.
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
./.venv/bin/pip install --quiet playwright
./.venv/bin/playwright install firefox
echo "xshot ready: ./xshot <post-url> -o out.png"
