#!/usr/bin/env bash
# =============================================================================
# Integration test: deterministic Dockerfile fix patterns
# =============================================================================
# Thin wrapper around tests/test_deterministic_fixes.py — the Python module
# holds all patterns as raw strings (avoiding bash/JSON backslash corruption).
#
# Usage:
#   bash tests/test_deterministic_fixes.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Colours ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${CYAN}${BOLD}=== Deterministic Fix Pattern Integration Test ===${RESET}"
echo ""

# Run the Python test module and colorize its pipe-delimited output
python3 "$SCRIPT_DIR/test_deterministic_fixes.py" 2>&1 | while IFS='|' read -r status name detail; do
    case "$status" in
        PASS)
            echo -e "  ${GREEN}PASS${RESET}  $name"
            ;;
        FAIL)
            echo -e "  ${RED}FAIL${RESET}  $name"
            if [[ -n "${detail:-}" ]]; then
                echo -e "        ${RED}${detail}${RESET}"
            fi
            ;;
        "")
            # Empty line or non-pipe-delimited output (section headers, summary)
            echo "$name"
            ;;
        *)
            # Section headers and summary lines
            echo "$status $name $detail"
            ;;
    esac
done || true   # read returns non-zero on EOF; suppress with pipefail

# Propagate the Python exit code
exit "${PIPESTATUS[0]}"
