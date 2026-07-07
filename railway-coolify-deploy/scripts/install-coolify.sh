#!/usr/bin/env bash
# =============================================================================
# install-coolify.sh
# Run ON the droplet as root after provision-droplet.sh finishes.
# Installs Coolify v4 via the official installer.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# Re-source .env from local path so we can read DOMAIN, etc.
if [[ -f "${ROOT_DIR}/.env" ]]; then
    # shellcheck disable=SC1091
    set -a; source "${ROOT_DIR}/.env"; set +a
fi

# Must be root on the droplet
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "This script must be run as root on the droplet. SSH in as root@<ip> and retry."
fi

COOLIFY_VERSION="4.0.0"
COOLIFY_INSTALL_URL="https://cdn.coollabs.io/coolify/install.sh"
COOLIFY_DATA_DIR="/data/coolify"

# Refuse to run without a real DOMAIN — Coolify's APP_URL will be broken otherwise.
: "${DOMAIN:?DOMAIN must be set (run: cp .env.example .env, edit, scp to /opt/railway-coolify-deploy)}"

info "Installing prerequisites: curl, git, openssl, sudo..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null
apt-get install -y --no-install-recommends curl git openssl sudo jq ca-certificates >/dev/null

info "Verifying Ubuntu version..."
. /etc/os-release
if [[ "${ID}" != "ubuntu" ]]; then
    warn "Expected Ubuntu, got ${ID}. Proceeding anyway — Coolify docs recommend Ubuntu 24.04."
fi

info "Rendering Coolify config (${COOLIFY_DATA_DIR}/.env)..."
mkdir -p "${COOLIFY_DATA_DIR}"
# Coolify reads /data/coolify/.env for setup-time secrets
cat > "${COOLIFY_DATA_DIR}/.env" <<EOF
# Auto-populated by install-coolify.sh
APP_NAME=Coolify
APP_KEY=base64:$(openssl rand -base64 32 | tr -d '\n')
APP_URL=https://coolify.${DOMAIN:-localhost}
APP_DEBUG=false
DB_CONNECTION=sqlite
DB_DATABASE=database.sqlite
# Mirror the values from your local .env so the panel matches
ADMIN_EMAIL=${COOLIFY_ADMIN_EMAIL:-admin@localhost}
EOF

chmod 600 "${COOLIFY_DATA_DIR}/.env"

info "Running the official Coolify installer (this takes 3-5 minutes)..."
curl -fsSL "${COOLIFY_INSTALL_URL}" | bash

# Wait for the Coolify container to start accepting connections.
# First boot is slow: image pulls, migrations run, key generation. Allow 6 min.
info "Waiting for Coolify UI on port 8000 (up to 6 min — first boot downloads images and runs migrations)..."
for i in $(seq 1 90); do                       # 90 × 4s = 360s
    if curl -sf -k http://localhost:8000/ -o /dev/null 2>&1; then
        info "Coolify UI is responding on port 8000 (after ${i} polls)"
        break
    fi
    if [[ "${i}" -eq 90 ]]; then
        warn "Coolify did not come up within 6 min. Last 40 lines of logs:"
        (cd "${COOLIFY_DATA_DIR}" 2>/dev/null && docker compose logs --tail=40 coolify 2>/dev/null) || true
        die "  → Re-run after docker compose up finishes; check /var/log/cloud-init-output.log"
    fi
    sleep 4
done

# Smoke-test: the auto-redirect from / to /install is the canonical "boot complete" signal.
# Without this, the script may exit on the FIRST http-served response (which is the splash
# page) while migrations are still running.
info "Confirming setup wizard is reachable (auto-redirect / → /install)..."
for i in $(seq 1 30); do
    LOC=$(curl -s -o /dev/null -w "%{http_code}|%{redirect_url}" -k http://localhost:8000/ || echo "000|")
    if [[ "${LOC}" == 30* || "${LOC}" == 20* ]]; then
        info "Setup wizard reachable (got ${LOC%%|*})"
        break
    fi
    sleep 5
done

info ""
info "================================================================"
info "Coolify is running. UI is on http://$(hostname -I | awk '{print $1}'):8000"
info "================================================================"
info "Next steps (DO THESE IN YOUR BROWSER, then back on your laptop):"
info ""
info "  1. Open http://<droplet-ip>:8000 and complete the registration form"
info "     - Use these values from .env:"
info "       email:    ${COOLIFY_ADMIN_EMAIL:-admin@localhost}"
info "       password: <the value of COOLIFY_ADMIN_PASSWORD in your .env>"
info ""
info "  2. After registration: Settings → API Tokens → Create token"
info "     - Copy the token and on YOUR LOCAL MACHINE, update .env:"
info "       COOLIFY_API_TOKEN=<the-token>"
info ""
info "  3. Add a wildcard DNS record (if not already done):"
info "       *.${DOMAIN:-yourdomain.com}    A    $(hostname -I | awk '{print $1}')"
info "       coolify.${DOMAIN:-yourdomain.com}   A    $(hostname -I | awk '{print $1}')"
info ""
warn "Until step 2 is complete, register-services.sh will not work."
