#!/usr/bin/env bash
# =============================================================================
# Integration test: health check fallback polling
# =============================================================================
# Starts a busybox httpd server that returns 404 on /health but 200 on /,
# then runs the same fallback logic as scripts/pipeline.py step_4_build_test
# to verify:
#   1. /health returns 404
#   2. / returns 200
#   3. Fallback polling finds / after /health fails with 404
#   4. No endpoint is tried twice (dedup)
#   5. All other fallback endpoints return 404
#
# Usage:
#   bash tests/test_health_fallbacks.sh
# =============================================================================

set -euo pipefail

# ── Colours ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── State ──
PORT=9090                           # avoid conflicting with real services
TEST_DIR=$(mktemp -d)
HTTPD_PID=""
PASSES=0
FAILS=0

# ── Health fallback endpoints (mirrors _HEALTH_FALLBACK_ENDPOINTS in pipeline.py) ──
FALLBACKS=(
    "/health"
    "/health/ready"
    "/healthz"
    "/ping"
    "/api/health"
    "/"
)

# ── Cleanup trap ──
cleanup() {
    if [[ -n "${HTTPD_PID:-}" ]] && kill -0 "$HTTPD_PID" 2>/dev/null; then
        kill "$HTTPD_PID" 2>/dev/null || true
        wait "$HTTPD_PID" 2>/dev/null || true
    fi
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# ── Setup: busybox httpd with only an index.html at / ──
echo "<html><body>OK</body></html>" > "$TEST_DIR/index.html"
# All other paths (including /health) have no file → busybox returns 404

if ! command -v busybox &>/dev/null; then
    echo -e "${YELLOW}SKIP${RESET}: busybox not found — install busybox to run this test"
    exit 0
fi

# Start httpd in foreground-with-logging mode (-f = foreground, no daemonize)
busybox httpd -f -p "$PORT" -h "$TEST_DIR" &
HTTPD_PID=$!

# Wait for server to be ready
for i in $(seq 1 10); do
    if kill -0 "$HTTPD_PID" 2>/dev/null && \
       curl -s -o /dev/null "http://localhost:${PORT}/" 2>/dev/null; then
        break
    fi
    sleep 0.2
done

if ! kill -0 "$HTTPD_PID" 2>/dev/null; then
    echo -e "${RED}FAIL${RESET}: busybox httpd failed to start"
    exit 1
fi

echo -e "${CYAN}${BOLD}=== Health Check Fallback Integration Test ===${RESET}"
echo ""

# ── Helper: try_endpoint (mirrors _try_endpoint in pipeline.py) ──
try_endpoint() {
    local endpoint="$1"
    curl -s -o /dev/null -w "%{http_code}" \
         "http://localhost:${PORT}${endpoint}" 2>/dev/null || echo "000"
}

# ═════════════════════════════════════════════════════════════════════════
# Test 1: /health returns 404 (configured endpoint — "not found", not broken)
# ═════════════════════════════════════════════════════════════════════════
echo -n "Test 1: /health returns 404... "
CODE=$(try_endpoint "/health")
if [[ "$CODE" == "404" ]]; then
    echo -e "${GREEN}PASS${RESET} (HTTP $CODE)"
    ((PASSES++))
else
    echo -e "${RED}FAIL${RESET} (expected 404, got HTTP $CODE)"
    ((FAILS++))
fi

# ═════════════════════════════════════════════════════════════════════════
# Test 2: / returns 200 (the ultimate fallback)
# ═════════════════════════════════════════════════════════════════════════
echo -n "Test 2: / returns 200... "
CODE=$(try_endpoint "/")
if [[ "$CODE" == "200" ]]; then
    echo -e "${GREEN}PASS${RESET} (HTTP $CODE)"
    ((PASSES++))
else
    echo -e "${RED}FAIL${RESET} (expected 200, got HTTP $CODE)"
    ((FAILS++))
fi

# ═════════════════════════════════════════════════════════════════════════
# Test 3: all fallback endpoints return their expected codes
# ═════════════════════════════════════════════════════════════════════════
echo ""
echo "Test 3: fallback endpoint matrix..."
ALL_PASS=true
for ep in "${FALLBACKS[@]}"; do
    CODE=$(try_endpoint "$ep")
    if [[ "$ep" == "/" ]]; then
        if [[ "$CODE" == "200" ]]; then
            echo -e "  $ep → HTTP $CODE ${GREEN}✓${RESET} (root serves index.html)"
        else
            echo -e "  $ep → HTTP $CODE ${RED}✗ expected 200${RESET}"
            ALL_PASS=false
        fi
    else
        if [[ "$CODE" == "404" ]]; then
            echo -e "  $ep → HTTP $CODE ${GREEN}✓${RESET}"
        else
            echo -e "  $ep → HTTP $CODE ${RED}✗ expected 404${RESET}"
            ALL_PASS=false
        fi
    fi
done
if $ALL_PASS; then
    echo -e "  → ${GREEN}PASS${RESET}"
    ((PASSES++))
else
    echo -e "  → ${RED}FAIL${RESET}"
    ((FAILS++))
fi

# ═════════════════════════════════════════════════════════════════════════
# Test 4: full pipeline fallback simulation
# ═════════════════════════════════════════════════════════════════════════
echo ""
echo "Test 4: simulated pipeline fallback logic..."
HEALTH_ENDPOINT="/health"
TRIED_ENDPOINTS=("$HEALTH_ENDPOINT")
HEALTH_OK=false
WORKING_ENDPOINT=""
LAST_CODE=""

# Step A — try configured endpoint first
CODE=$(try_endpoint "$HEALTH_ENDPOINT")
LAST_CODE="$CODE"
echo "  Configured endpoint $HEALTH_ENDPOINT → HTTP $CODE"

if [[ "$CODE" == 2* ]]; then
    HEALTH_OK=true
    WORKING_ENDPOINT="$HEALTH_ENDPOINT"
elif [[ "$CODE" == "404" ]]; then
    # Endpoint doesn't exist — poll fallback list
    echo "  → 404 received, polling fallback endpoints..."
    for fb in "${FALLBACKS[@]}"; do
        # Dedup: skip if already tried
        ALREADY_TRIED=false
        for t in "${TRIED_ENDPOINTS[@]}"; do
            [[ "$t" == "$fb" ]] && ALREADY_TRIED=true && break
        done
        $ALREADY_TRIED && continue

        TRIED_ENDPOINTS+=("$fb")
        FB_CODE=$(try_endpoint "$fb")
        LAST_CODE="$FB_CODE"
        echo -n "    $fb → HTTP $FB_CODE"
        if [[ "$FB_CODE" == 2* ]]; then
            HEALTH_OK=true
            WORKING_ENDPOINT="$fb"
            echo -e " ${GREEN}✓ FOUND${RESET}"
            break
        else
            echo ""
        fi
    done
    if ! $HEALTH_OK; then
        echo "  → All ${#TRIED_ENDPOINTS[@]} endpoint(s) failed (last: HTTP $LAST_CODE)"
    fi
else
    # Non-404 failure (500, 503, etc.) — service is broken, skip fallbacks
    echo "  → Non-404 failure (HTTP $CODE) — skipping fallback poll"
fi

# Assertions
if $HEALTH_OK; then
    echo -e "  → ${GREEN}PASS${RESET} (health OK via $WORKING_ENDPOINT)"
    ((PASSES++))
else
    echo -e "  → ${RED}FAIL${RESET} (no fallback returned 2xx)"
    ((FAILS++))
fi

# ═════════════════════════════════════════════════════════════════════════
# Test 5: dedup — /health was not retried as a fallback
# ═════════════════════════════════════════════════════════════════════════
echo ""
echo -n "Test 5: dedup — /health tried exactly once... "
HEALTH_COUNT=0
for t in "${TRIED_ENDPOINTS[@]}"; do
    [[ "$t" == "/health" ]] && ((HEALTH_COUNT++)) || true
done
if [[ "$HEALTH_COUNT" -eq 1 ]]; then
    echo -e "${GREEN}PASS${RESET} (/health tried $HEALTH_COUNT time(s))"
    ((PASSES++))
else
    echo -e "${RED}FAIL${RESET} (/health tried $HEALTH_COUNT time(s), expected 1)"
    ((FAILS++))
fi

# ═════════════════════════════════════════════════════════════════════════
# Test 6: all tried endpoints are unique
# ═════════════════════════════════════════════════════════════════════════
echo -n "Test 6: no duplicate endpoint attempts... "
declare -A SEEN
DUPE=false
for t in "${TRIED_ENDPOINTS[@]}"; do
    if [[ -n "${SEEN[$t]:-}" ]]; then
        echo -e "${RED}FAIL${RESET} ($t tried more than once)"
        DUPE=true
        break
    fi
    SEEN[$t]=1
done
if ! $DUPE; then
    echo -e "${GREEN}PASS${RESET} (${#TRIED_ENDPOINTS[@]} unique endpoints tried)"
    ((PASSES++))
else
    ((FAILS++))
fi

# ═════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}${BOLD}=== Results: $PASSES passed, $FAILS failed ===${RESET}"

if [[ "$FAILS" -gt 0 ]]; then
    echo -e "${RED}Some tests failed.${RESET}"
    exit 1
fi

echo -e "${GREEN}${BOLD}All tests passed!${RESET}"
