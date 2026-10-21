#!/usr/bin/env bash
# Convenience runner: creates a venv (if missing), installs deps, runs the
# pipeline against today's sample file, then runs the test suite.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

python pipeline.py --source data/raw_orders_2026-08-03.csv

echo ""
echo "Running tests..."
pytest tests/ -q
