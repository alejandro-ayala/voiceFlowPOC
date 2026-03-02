#!/usr/bin/env bash
# Local CI lint pipeline — mirrors .github/workflows/ci.yml (lint-format job)
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNED=0

run_step() {
    local label="$1"
    local blocking="$2"
    shift 2

    printf "\n${NC}--- %s ---\n" "$label"
    if "$@"; then
        printf "${GREEN}PASS${NC} %s\n" "$label"
        ((PASSED+=1))
    elif [ "$blocking" = "true" ]; then
        printf "${RED}FAIL${NC} %s\n" "$label"
        ((FAILED+=1))
    else
        printf "${YELLOW}WARN${NC} %s (non-blocking)\n" "$label"
        ((WARNED+=1))
    fi
}

cd "$(git rev-parse --show-toplevel)"

run_step "ruff check (lint)"   true  poetry run ruff check .
run_step "ruff format --check" true  poetry run ruff format --check .
run_step "mypy (type check)"   false poetry run mypy application/ business/ shared/ integration/ presentation/

printf "\n========================================\n"
printf "Results: ${GREEN}${PASSED} passed${NC}"
[ "$WARNED" -gt 0 ] && printf ", ${YELLOW}${WARNED} warned${NC}"
[ "$FAILED" -gt 0 ] && printf ", ${RED}${FAILED} failed${NC}"
printf "\n========================================\n"

[ "$FAILED" -eq 0 ]
