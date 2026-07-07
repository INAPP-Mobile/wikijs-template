#!/usr/bin/env bash
# =============================================================================
# verify.sh
# Smoke-test each deployed service by hitting its configured subdomain.
# Exits 0 if all pass within 60s, 1 otherwise.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[SKIP]${NC} $1"; }

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
    echo "FATAL: .env not found" >&2; exit 1
fi
# shellcheck disable=SC1091
set -a; source "${ROOT_DIR}/.env"; set +a

# name|subdomain|expected_status|path
declare -a CHECKS=(
    "Coolify UI|coolify|200|/"
    "Gotify|${GOTIFY_SUBDOMAIN}|200|/health"
    "Memos|${MEMOS_SUBDOMAIN}|200|/health"
    "Kanboard|${KANBOARD_SUBDOMAIN}|200|/healthcheck.php"
    "Netdata|${NETDATA_SUBDOMAIN}|200|/api/v1/info"
    "Stirling-PDF|${STIRLING_SUBDOMAIN}|200|/api/v1/info/status"
    "Node-RED|${NODERED_SUBDOMAIN}|200|/"
)

FAIL_COUNT=0
TOTAL_COUNT=0

for row in "${CHECKS[@]}"; do
    IFS='|' read -r NAME SUBDOMAIN EXPECT PATH_ <<< "${row}"
    [[ -z "${SUBDOMAIN}" || "${SUBDOMAIN}" == "-" ]] && continue
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    URL="https://${SUBDOMAIN}.${DOMAIN}${PATH_}"

    # Fail-fast DNS diagnostic: if the subdomain doesn't resolve, no amount of curl retries helps.
    # `dig` is not always installed — fall back to `getent hosts` (glibc) or `host` (bind-tools).
    RESOLVED=""
    if command -v dig >/dev/null 2>&1; then
        RESOLVED=$(dig +short "${SUBDOMAIN}.${DOMAIN}" 2>/dev/null | head -n1)
    elif command -v getent >/dev/null 2>&1; then
        getent hosts "${SUBDOMAIN}.${DOMAIN}" 2>/dev/null | awk '{print $1}' | head -n1 \
            | tr -d '\n' | read -r RESOLVED
    elif command -v host >/dev/null 2>&1; then
        host -W 2 "${SUBDOMAIN}.${DOMAIN}" 2>/dev/null | awk '/has address/ {print $4; exit}' \
            | tr -d '\n' | read -r RESOLVED
    fi
    if [[ -z "${RESOLVED}" ]]; then
        fail "${NAME} → ${URL}  (DNS does NOT resolve — wildcard A record missing?)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # Try up to ~30s of retries per service. Stirling-PDF cold-start can take
    # 20s of JVM warm-up before responding 200.
    LAST_CODE="000"
    SUCCESS=0
    for i in $(seq 1 6); do
        LAST_CODE=$(curl -sk -o /dev/null -w "%{http_code}" \
            --max-time 10 \
            "${URL}" 2>/dev/null || echo "000")
        # 2xx and 3xx (redirects from / to /login) count as healthy
        if [[ "${LAST_CODE}" =~ ^2[0-9][0-9]$ || "${LAST_CODE}" =~ ^3[0-9][0-9]$ ]]; then
            pass "${NAME} → ${URL} (HTTP ${LAST_CODE})"
            SUCCESS=1
            break
        fi
        # 5xx / 000 = warmup; keep retrying
        if [[ "${LAST_CODE}" == "000" || "${LAST_CODE}" =~ ^5[0-9][0-9]$ ]]; then
            echo -n "." >&2; sleep 5; continue
        fi
        # 4xx (non-expected) is a hard failure — stop retrying
        break
    done

    if [[ "${SUCCESS}" -eq 0 ]]; then
        if [[ "${LAST_CODE}" == "000" ]]; then
            fail "${NAME} → ${URL}  (TIMEOUT after 6 retries)"
        else
            fail "${NAME} → ${URL}  (HTTP ${LAST_CODE})"
        fi
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

echo ""
echo "================================================================"
echo "Results: $((TOTAL_COUNT - FAIL_COUNT))/${TOTAL_COUNT} healthy"
echo "================================================================"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
    echo ""
    echo "Common fixes:"
    echo "  1. Coolify UI → Project → <service> → Logs — check for build errors"
    echo "  2. dig <subdomain>.${DOMAIN} +short → must resolve to droplet IP"
    echo "  3. UFW: ufw status (must allow 80, 443, 8000)"
    exit 1
fi

exit 0
