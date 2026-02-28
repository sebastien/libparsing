#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$BASE/lib-testing.sh"

if [ $# == 0 ]; then
	FILES=$(find "$BASE" -name "*.*")
else
	FILES=$*
fi

test-start

for TEST in $FILES; do
	case "$TEST" in
	*/lib-*.sh) ;;
	*/harness.sh) ;;
	*/*.sh)
		export TEST_COUNT
		if test-run "${DIM}»${PURPLE}" "$TEST"; then
			test-ok "Unit test succeeded: ${YELLOW}$(realpath --relative-to="$PWD" "$TEST")"
		else
			test-fail "Unit test failed: ${RED}$(realpath --relative-to="$PWD" "$TEST")"
		fi
		;;
	esac
done

if test-end; then
	echo "${GREEN}EOK${RESET}"
else
	echo "${RED}E!!${RESET}"
fi
# EOF
