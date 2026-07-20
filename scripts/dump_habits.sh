#!/usr/bin/env bash
# Pull all habits.db records from the live Railway volume.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
railway ssh --service pleasing-nurturing -- python3 < scripts/dump_habits.py
