# Coolify on DigitalOcean — Railway-Style Template Gallery

This bundle stands up [Coolify v4](https://coolify.io) on a single **$24/mo DigitalOcean
Droplet** and wires it as a **one-click deploy gallery** for the 6 INAPP-Mobile
Railway templates. End result: a Railway-like UI on your own infrastructure
where each template is a click-to-deploy service, with Traefik-managed HTTPS,
persistent volumes, and a unified admin panel.

```
                                     DigitalOcean Droplet ($24/mo, 4GB)
                                                  │
        ┌─────────────────────────────────────────┴─────────────────────────────────────────────┐
        │                                       │                                               │
   ┌────▼────┐   ┌────────────┐   ┌──────────┐   ┌─────────┐   ┌───────────┐   ┌───────┐   ┌─────▼─────┐
   │ Gotify  │   │   Memos    │   │ Kanboard │   │ Netdata │   │ Stirling  │   │ Node-  │   │  Coolify  │
   │ :8080   │   │ :5230      │   │ :80      │   │ :19999  │   │ PDF       │   │ RED    │   │   Admin   │
   │         │   │   + Postgres│  │  + Postgres│ │         │   │ :8080     │   │ :1880  │   │   :8000   │
   └─────────┘   └────────────┘   └──────────┘   └─────────    └───────────┘   └───────┘   └───────────┘
                              ▲
                              │
                              │ Traefik reverse proxy (auto-SSL)
                              │
                       https://*.yourdomain.com
```

## What you'll have at the end

| Item | Where | Cost |
|---|---|---|
| Coolify admin panel | `https://coolify.yourdomain.com` | $0 |
| Gotify demo | `https://gotify.yourdomain.com` | $0 (SQLite mode) |
| Memos demo | `https://memos.yourdomain.com` | $0 in SQLite mode |
| Kanboard demo | `https://kanboard.yourdomain.com` | $0 in SQLite mode |
| Netdata monitoring | `https://netdata.yourdomain.com` | $0 |
| Stirling-PDF demo | `https://pdf.yourdomain.com` | $0 |
| Node-RED editor | `https://flows.yourdomain.com` | $0 |
| DO Managed Postgres (optional, shared by Memos+Kanboard) | from `coolify` UI | $15/mo |
| **Droplet (4 GB, backups enabled)** | DO `s-2vcpu-4gb` | **$24/mo base + ~$4.80/mo backups = ~$29/mo** |
| **Total minimum** | | **$29/mo** for the full gallery |
| **Total if you add managed Postgres** | | **$44/mo** |

Read [`docs/architecture.md`](docs/architecture.md) for sizing rationale and
multi-tenancy options.

## Prerequisites

You need **once**, before starting:

1. **DigitalOcean account** with billing set up
2. **A domain you control** (e.g. `yourdomain.com`) — Cloudflare recommended for easy DNS
3. **`doctl` CLI** installed and authenticated:
   ```bash
   # macOS
   brew install doctl
   doctl auth init   # paste your DO API token
   ```
4. **An SSH key on your local machine** — we'll inject it into the droplet
5. **A wildcard DNS A record** (we'll create per-service subdomains):
   ```
   *.yourdomain.com    A    <DROPLET_IP>
   coolify.yourdomain.com  A    <DROPLET_IP>
   ```

## Quick start (≈ 20 min)

```bash
# 1. Configure
cd railway-coolify-deploy
cp .env.example .env
$EDITOR .env           # set DOMAIN, DO_REGION, DO_SSH_KEY_FINGERPRINT, COOLIFY_DROPLET_NAME

# 2. Provision the droplet (≈ 90s for the DO call + 60s for SSH)
./scripts/provision-droplet.sh
#   → prints the droplet IP

# 3. Add DNS records (Cloudflare recommended):
#       *.yourdomain.com       A    <droplet-ip>
#       coolify.yourdomain.com A    <droplet-ip>

# 4. Copy this directory onto the droplet and install Coolify
DROPLET_IP=$(doctl compute droplet get coolify-gallery --format PublicIPv4 --no-header)
scp -r . root@${DROPLET_IP}:/opt/railway-coolify-deploy/
ssh root@${DROPLET_IP}
# On the droplet:
cd /opt/railway-coolify-deploy
bash ./scripts/install-coolify.sh
#   → completes in 3–6 min (image download + migrations)
#   → prints URL+credentials for the Coolify admin UI

# 5. (Browser, ~ 2 min) Open http://<droplet-ip>:8000, complete the
#    registration form, then Settings → API Tokens → Create token.

# 6. Back on your LOCAL machine — paste the token into .env:
$EDITOR .env           # set COOLIFY_API_TOKEN=<the-token>

# 7. Register the 6 services via Coolify API
./scripts/register-services.sh
#   → wait 3-5 min after for builds

# 8. Smoke test
./scripts/verify.sh
```

> **Why these steps aren't combined into one script:** droplet creation
> requires your DO credentials; Coolify install requires running as root on
> the droplet; registering services requires a manually-minted API token
> from the Coolify UI (which needs an interactive browser). Each step has a
> distinct auth boundary.

## What this bundle does **NOT** do

- ❌ It does not provision databases (Coolify can do this from its UI; we
  pre-create one shared managed Postgres for cost efficiency).
- ❌ It does not modify the existing 6 Railway template repos (you may want
  to add a "Deploy to DO" badge to their READMEs — see follow-ups).
- ❌ It does not export Coolify configs to Terraform (out of scope; there are
  third-party Coolify→Terraform tools if needed).
- ❌ It does not set up backups (use Coolify's built-in scheduled backups to
  DO Spaces, ~$1/mo for a 10GB bucket, configured via UI).

## File layout

```
railway-coolify-deploy/
├── README.md                  ← you are here
├── .env.example               ← copy to .env and fill in
├── scripts/
│   ├── provision-droplet.sh   ← uses doctl to create the $24/mo droplet
│   ├── install-coolify.sh     ← one-shot Coolify install on Ubuntu 24.04
│   ├── bootstrap-coolify.sh   ← post-install: admin email, initial secrets
│   ├── register-services.sh   ← 6× Coolify API calls to create the services
│   └── verify.sh              ← smoke tests each deployed service
├── templates/                 ← per-service env var defaults
│   ├── gotify.env
│   ├── memos.env
│   ├── kanboard.env
│   ├── netdata.env
│   ├── stirling-pdf.env
│   └── node-red.env
├── docs/
│   ├── architecture.md        ← design rationale + service matrix
│   └── api-reference.md       ← Coolify v4 endpoints actually used
└── .gitignore
```

## After running, the user experience

1. Visitor lands on `https://coolify.yourdomain.com`
2. Logs in (your admin token)
3. Sees a dashboard with **6 deployed services**: Gotify, Memos, Kanboard,
   Netdata, Stirling-PDF, Node-RED
4. Each service has its own HTTPS URL, health-check, logs, env vars editor,
   redeploy button
5. Public users browsing `memos.yourdomain.com` see a working Memos instance
6. **New visitors** (your prospective users) can be onboarded by:
   - Forking the public GitHub repo, OR
   - Clicking the readout link to deploy their own instance via Cloudflare DNS
     repoint + Coolify's `Save as Template` JSON export

## Next steps

When you're ready to make this **multi-user** (so visitors can deploy their own
instance on your droplet), see
[`docs/architecture.md#multi-tenancy`](docs/architecture.md).
For now: admin-only is the right default for a portfolio/personal setup.

## Rollback / teardown

```bash
# Destroy the droplet (irreversible)
doctl compute droplet delete coolify-gallery --force

# Cloudflare: remove the wildcard A record
```

## Support / troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Coolify UI shows "Invalid Token" after install | Initial setup didn't complete | `ssh root@... 'cd /data/coolify && docker compose logs -f'` |
| Service stuck in "starting" | Build error in upstream Dockerfile | `./scripts/register-services.sh --rebuild gotify` |
| 502 from `memos.yourdomain.com` | DNS not pointing to droplet | `dig memos.yourdomain.com +short` → must show droplet IP |
| Out of disk | Persistent volume filled | `doctl compute droplet-action snapshot ...` first, then resize |
| Postgres connection refused | Managed DB in different region | Recreate in `nyc3` to match droplet |

See [`docs/architecture.md`](docs/architecture.md) for the full troubleshooting
matrix and design rationale.
