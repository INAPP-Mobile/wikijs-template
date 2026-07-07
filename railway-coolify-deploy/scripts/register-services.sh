#!/usr/bin/env bash
# =============================================================================
# register-services.sh
# Run LOCALLY. Calls the Coolify v4 API to create the 6 services that deploy
# the INAPP-Mobile Railway templates via the Dockerfile Build Pack.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# Load .env
[[ -f "${ROOT_DIR}/.env" ]] || die ".env not found"
# shellcheck disable=SC1091
set -a; source "${ROOT_DIR}/.env"; set +a

# Validate required vars
: "${COOLIFY_API_TOKEN:?Set COOLIFY_API_TOKEN in .env (mint from Coolify UI → Settings → API Tokens)}"
: "${COOLIFY_BASE_URL:?Set COOLIFY_BASE_URL like https://coolify.example.com/api/v1}"

command -v curl >/dev/null 2>&1 || die "curl missing"
command -v jq >/dev/null 2>&1 || die "jq missing — apt install jq or brew install jq"

# ----------------------------------------------------------------------------
# Service configuration table — the single source of truth for what to create.
# Each row: name | git repo | subdomain | internal port | env file | params
# ----------------------------------------------------------------------------
#   -1 in subdomain disables creation
#   Coolify will pull the Dockerfile from each repo at the pinned ref
# ----------------------------------------------------------------------------
declare -a SERVICES=(
    # name|git_repo|git_branch|subdomain|internal_port|env_file|healthcheck_path|description
    "gotify|https://github.com/INAPP-Mobile/railway-gotify|main|${GOTIFY_SUBDOMAIN}|${GOTIFY_PORT}|gotify.env|/health|Self-hosted push notification server"
    "memos|https://github.com/INAPP-Mobile/railway-memos|main|${MEMOS_SUBDOMAIN}|${MEMOS_PORT}|memos.env|/health|Open-source timeline note-taking"
    "kanboard|https://github.com/INAPP-Mobile/railway-kanboard|main|${KANBOARD_SUBDOMAIN}|${KANBOARD_PORT}|kanboard.env|/healthcheck.php|Kanban project management"
    "netdata|https://github.com/INAPP-Mobile/railway-netdata|main|${NETDATA_SUBDOMAIN}|${NETDATA_PORT}|netdata.env|/api/v1/info|Real-time monitoring dashboard"
    "stirling-pdf|https://github.com/INAPP-Mobile/railway-stirling-pdf|main|${STIRLING_SUBDOMAIN}|${STIRLING_PORT}|stirling-pdf.env|/api/v1/info/status|PDF manipulation toolkit"
    "node-red|https://github.com/INAPP-Mobile/railway-node-red|main|${NODERED_SUBDOMAIN}|${NODERED_PORT}|node-red.env|/|Low-code IoT workflow editor"
)

# ----------------------------------------------------------------------------
# Helper: GET /projects to find project UUID we should attach applications to.
# Coolify v4 has a "Default" project — we'll create our own "INAPP Templates"
# project to keep things organized.
# ----------------------------------------------------------------------------
COOLIFY_AUTH=(-H "Authorization: Bearer ${COOLIFY_API_TOKEN}")
COOLIFY_JSON=(-H "Content-Type: application/json")

PROJECT_NAME="INAPP Railway Templates"
PROJECT_DESC="Self-hosted gallery of 6 INAPP Railway templates deployed via Coolify"

info "Finding or creating project: ${PROJECT_NAME}"
PROJECT_UUID=$(curl -fsS "${COOLIFY_BASE_URL}/projects" "${COOLIFY_AUTH[@]}" \
    | jq -r --arg name "${PROJECT_NAME}" \
        '.[] | select(.name == $name) | .uuid' \
    | head -n 1 || true)

if [[ -z "${PROJECT_UUID}" ]]; then
    info "Creating new project..."
    PROJECT_UUID=$(curl -fsS -X POST "${COOLIFY_BASE_URL}/projects" \
        "${COOLIFY_AUTH[@]}" "${COOLIFY_JSON[@]}" \
        -d "$(jq -n \
            --arg name "${PROJECT_NAME}" \
            --arg desc "${PROJECT_DESC}" \
            '{name: $name, description: $desc}')" \
        | jq -r '.uuid')
    info "Project created: ${PROJECT_UUID}"
else
    info "Project exists: ${PROJECT_UUID}"
fi

# ----------------------------------------------------------------------------
# Helper: ensure the destination server (Coolify tracks the droplet as a
# "Server" or "Destination"). We need its UUID to attach resources.
# ----------------------------------------------------------------------------
info "Finding destination server..."
SERVER_UUID=$(curl -fsS "${COOLIFY_BASE_URL}/servers" "${COOLIFY_AUTH[@]}" \
    | jq -r --arg name "${COOLIFY_DROPLET_NAME}" \
        '.[] | select(.name == $name) | .uuid' \
    | head -n 1 || true)

if [[ -z "${SERVER_UUID}" ]]; then
    die "Server '${COOLIFY_DROPLET_NAME}' not found in Coolify. Did you run install-coolify.sh?"
fi
info "Using server: ${SERVER_UUID}"

# ----------------------------------------------------------------------------
# Main loop: create one application per service
# ----------------------------------------------------------------------------
for row in "${SERVICES[@]}"; do
    IFS='|' read -r NAME REPO BRANCH SUBDOMAIN PORT ENV_FILE HC_PATH DESC <<< "${row}"

    if [[ -z "${SUBDOMAIN}" || "${SUBDOMAIN}" == "-" ]]; then
        warn "Skipping ${NAME}: no subdomain configured"
        continue
    fi

    DOMAIN="${SUBDOMAIN}.${DOMAIN}"

    # Skip if already exists in this project
    info "Checking if ${NAME} already exists in project..."
    EXISTING=$(curl -fsS "${COOLIFY_BASE_URL}/projects/${PROJECT_UUID}/applications" \
        "${COOLIFY_AUTH[@]}" \
        | jq -r --arg n "${NAME}" '.[] | select(.name == $n) | .uuid' \
        | head -n 1 || true)

    if [[ -n "${EXISTING}" ]]; then
        warn "${NAME} already exists as ${EXISTING}; skipping"
        continue
    fi

    # Build env vars JSON from templates/<NAME>.env (KEY=value lines → array)
    ENV_JSON="[]"
    ENV_FILE_PATH="${ROOT_DIR}/templates/${ENV_FILE}"
    if [[ -f "${ENV_FILE_PATH}" ]]; then
        ENV_JSON=$(grep -v '^[[:space:]]*$\|^#' "${ENV_FILE_PATH}" \
            | awk -F'=' '{
                key=$1; $1="";
                val=substr($0, index($0, "=")+1);
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", key);
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", val);
                # Coolify env shape: key, value, plus the two boolean flags that exist in
                # v4.0.0 stable. Do NOT add `is_literal` — it appeared briefly in some 4.0 betas
                # and 422s the request in v4.0.0 stable.
                printf("{\"key\":\"%s\",\"value\":\"%s\",\"is_multiline\":false,\"is_secret\":false}", key, val);
              }' \
            | jq -s '.')
    fi

    info "Creating application: ${NAME} → ${DOMAIN}:${PORT}"
    # NOTE: do NOT include `instant_deploy` — it was renamed/removed in some Coolify v4.x
    # betas and breaks the request with a 422 if sent. We explicitly POST /deploy below.
    APP_PAYLOAD=$(jq -n \
        --arg name "${NAME}" \
        --arg desc "${DESC}" \
        --arg repo "${REPO}" \
        --arg branch "${BRANCH}" \
        --arg domain "${DOMAIN}" \
        --argjson port "${PORT}" \
        --arg healthcheck "${HC_PATH}" \
        --argjson envs "${ENV_JSON}" \
        '{
            name: $name,
            description: $desc,
            git_repository: $repo,
            git_branch: $branch,
            build_pack: "dockerfile",
            server_id: $server_uuid,
            ports_exposes: ($port | tostring),
            health_check_path: $healthcheck,
            health_check_port: ($port | tostring),
            health_check_method: "GET",
            health_check_interval: 30,
            health_check_timeout: 5,
            health_check_retries: 3,
            health_check_start_period: 30,
            fqdn: $domain,
            envs: $envs
        }')

    # Substitute the server uuid which is a shell var (jq can't read env vars)
    APP_PAYLOAD=$(echo "${APP_PAYLOAD}" | jq --arg suuid "${SERVER_UUID}" '.server_id = $suuid')

    RESPONSE=$(curl -fsS -X POST \
        "${COOLIFY_BASE_URL}/projects/${PROJECT_UUID}/applications/applications" \
        "${COOLIFY_AUTH[@]}" "${COOLIFY_JSON[@]}" \
        -d "${APP_PAYLOAD}" || echo "")

    if [[ -z "${RESPONSE}" ]]; then
        warn "${NAME}: API call failed. See the per-app log above. Continuing…"
        continue
    fi

    NEW_UUID=$(echo "${RESPONSE}" | jq -r '.uuid // empty')
    if [[ -z "${NEW_UUID}" ]]; then
        warn "${NAME}: API returned no uuid. Response: ${RESPONSE}"
        continue
    fi

    info "✓ ${NAME} created (uuid=${NEW_UUID}). Now deploying…"
    DEPLOY_RESPONSE=$(curl -fsS -X POST \
        "${COOLIFY_BASE_URL}/applications/${NEW_UUID}/deploy" \
        "${COOLIFY_AUTH[@]}" "${COOLIFY_JSON[@]}" \
        -d '{"tag": "initial"}' || echo "")
    if [[ -n "${DEPLOY_RESPONSE}" ]]; then
        info "  ✓ deployment queued for ${NAME}"
    else
        warn "  ! deploy queue failed for ${NAME}. Try via UI."
    fi
done

info ""
info "================================================================"
info "All services registered. Wait ~3-5 minutes for builds to complete."
info "================================================================"
info "  - Coolify admin:    https://coolify.${DOMAIN}"
info "  - This script does NOT verify builds — run ./scripts/verify.sh next"
info "  - Persistent storage (volumes) must be attached via the Coolify UI per service"
info "    (see docs/architecture.md §Service-by-service deploy plan)"
info "  - Stirling-PDF first build is slow (~5 min) due to large image layers"
info ""
