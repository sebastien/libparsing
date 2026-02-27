#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$BASE/lib-testing.sh"

test-init "C Parser PCSS Test"

# Build the test binary if needed
test-step "Building c-parser-pcss binary"
test-cmd make -C "$(dirname "$BASE")" dist/c-parser-pcss >/dev/null 2>&1

test-step "Running c-parser-pcss test"
PROJECT_ROOT="$(dirname "$BASE")"
# Set library path and run from project root
cd "$PROJECT_ROOT"
export LD_LIBRARY_PATH="$PROJECT_ROOT/dist${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
test-cmd "$PROJECT_ROOT/dist/c-parser-pcss" >/dev/null 2>&1

test-end
