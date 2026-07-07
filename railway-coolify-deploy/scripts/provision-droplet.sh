#!/usr/bin/env bash
# =============================================================================
# provision-droplet.sh
# Creates the $24/mo DigitalOcean Droplet that hosts Coolify + the 6 apps.
# Run this LOCALLY from your machine (doctl must be authenticated).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Color output
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# Load .env
if [[ ! -f "${ROOT_DIR}/.env" ]]; then
    die ".env not found. Copy .env.example to .env and fill in the values."
fi

# shellcheck disable=SC1091
set -a; source "${ROOT_DIR}/.env"; set +a

# Validate required vars
: "${DOMAIN:?DOMAIN must be set in .env}"
: "${DO_REGION:?DO_REGION must be set}"
: "${DO_SIZE:?DO_SIZE must be set}"
: "${DO_IMAGE:?DO_IMAGE must be set}"
: "${DO_SSH_KEY_FINGERPRINT:?DO_SSH_KEY_FINGERPRINT must be set}"
: "${COOLIFY_DROPLET_NAME:?COOLIFY_DROPLET_NAME must be set}"

command -v doctl >/dev/null 2>&1 || die "doctl not installed. brew install doctl or visit https://docs.digitalocean.com/reference/doctl/how-to/install/"

info "Checking if droplet ${COOLIFY_DROPLET_NAME} already exists..."
EXISTING_IP=$(doctl compute droplet list \
    --format "Name,PublicIPv4" --no-header \
    | awk -v name="${COOLIFY_DROPLET_NAME}" '$1 == name { print $2 }' \
    || true)

if [[ -n "${EXISTING_IP}" && "${EXISTING_IP}" != "-" ]]; then
    warn "Droplet ${COOLIFY_DROPLET_NAME} already exists at ${EXISTING_IP}."
    echo "If you want to recreate, run: doctl compute droplet delete ${COOLIFY_DROPLET_NAME} --force"
    echo "Public IPv4: ${EXISTING_IP}"
    exit 0
fi

# Cloud-init: open firewall for Coolify BEFORE install runs
# This makes the droplet reachable on ports 8000/6001/6002 for the initial
# dashboard setup, then we'll restrict via Cloudflare Access + Docker iptables
# once Coolify is up.
read -r -d '' CLOUD_INIT <<'EOF' || true
#cloud-config
package_update: true
package_upgrade: true
runcmd:
  - ufw --version || apt-get install -y ufw
  - ufw allow 22/tcp     comment 'SSH'
  - ufw allow 80/tcp     comment 'HTTP'
  - ufw allow 443/tcp    comment 'HTTPS'
  - ufw allow 8000/tcp   comment 'Coolify UI'
  - ufw allow 6001/tcp   comment 'Coolify realtime'
  - ufw allow 6002/tcp   comment 'Coolify terminal'
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw --force enable
  - sysctl -w vm.max_map_count=262144
  - echo "vm.max_map_count=262144" > /etc/sysctl.d/99-coolify.conf
  - mkdir -p /opt/railway-coolify-deploy
output: { all: '| tee -a /var/log/cloud-init-output.log' }
EOF

info "Creating droplet ${COOLIFY_DROPLET_NAME} (${DO_SIZE} in ${DO_REGION})..."
DOCTL_OUTPUT=$(doctl compute droplet create "${COOLIFY_DROPLET_NAME}" \
    --region "${DO_REGION}" \
    --size "${DO_SIZE}" \
    --image "${DO_IMAGE}" \
    --ssh-keys "${DO_SSH_KEY_FINGERPRINT}" \
    --enable-monitoring \
    --enable-backups \
    --user-data "${CLOUD_INIT}" \
    --tag-name "coolify,railway-templates" \
    --wait \
    --format "ID,Name,PublicIPv4,Status" \
    --no-header)

warn "Cost breakdown:"
echo "  Droplet base:    \$24.00/mo"
echo "  Backups (20%):   \$ 4.80/mo  (snapshot every 7 days)"
echo "  Monitoring:      included"
echo "  Estimated total: \$28.80/mo before database or overage costs"

# Parse the first line's IP (doctl prints one row per created droplet)
DROPLET_IP=$(echo "${DOCTL_OUTPUT}" | head -n 1 | awk '{print $3}')
DROPLET_STATUS=$(echo "${DOCTL_OUTPUT}" | head -n 1 | awk '{print $4}')

if [[ -z "${DROPLET_IP}" || "${DROPLET_IP}" == "-" ]]; then
    die "Failed to parse droplet IP from doctl output:\n${DOCTL_OUTPUT}"
fi

info "Droplet created: ${COOLIFY_DROPLET_NAME} @ ${DROPLET_IP} (${DROPLET_STATUS})"
info ""
info "Next steps (do them IN THIS ORDER):"
echo "  1. Wait ~60s for SSH to come online: ssh root@${DROPLET_IP}"
echo "  2. Add DNS records (Cloudflare recommended, before Coolify install):"
echo "       *.${DOMAIN}             A    ${DROPLET_IP}"
echo "       coolify.${DOMAIN}       A    ${DROPLET_IP}"
echo "  3. Copy this directory onto the droplet:"
echo "       scp -r ${ROOT_DIR}/* root@${DROPLET_IP}:/opt/railway-coolify-deploy/"
echo "  4. SSH in and run: cd /opt/railway-coolify-deploy && sudo bash ./scripts/install-coolify.sh"
echo ""
echo "When install-coolify.sh succeeds, save your API token into .env on"
echo "your LOCAL machine (COOLIFY_API_TOKEN=…) and run:"
echo "  ./scripts/register-services.sh"
echo "  ./scripts/verify.sh   # after ~5 min for builds"
echo ""
