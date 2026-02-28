#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$BASE/lib-testing.sh"

test-init "Python Recursive Test"

PROJECT_ROOT="$(dirname "$BASE")"

test-step "Running python-recursive.py"
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT/src/python:$PYTHONPATH" test-cmd python3 "$BASE/python-recursive.py" >/dev/null 2>&1

test-end
