# Architecture — Coolify on DigitalOcean

## Why Coolify + Droplet vs App Platform or Railway

| Criteria | DO App Platform | Coolify on DO Droplet | Railway |
|---|---|---|---|
| One-click deploy from public repo | ❌ (creates then iterates) | ✅ (registry at `:8000`) | ✅ (marketplace) |
| Multi-template **gallery UI** | ❌ | ✅ | ✅ |
| User cost to deploy | $5 + $15/mo DB | $0 (admin's bill) | $5–20/mo |
| GitHub Action fallback | ✅ (good) | ✅ (good) | ✅ (`railway up`) |
| Coolify commands | ❌ | Built-in | ❌ |
| Custom domains | ✅ per app | ✅ wildcard via Traefik | ✅ per app |
| Public GitHub → deploy | ✅ manual | ✅ automatic (UI) | ✅ publish to marketplace |
| Self-hosted PaaS feel | ❌ abstracted | ✅ native | ❌ abstracted |

The **gallery UI** is the key feature you're missing on App Platform and
Railway-from-DO. Coolify gives you precisely that at $24/mo + the cost of any
databases you provision.

## Service sizing matrix (per app)

It is tempting to run everything on `basic-xxs` (~$5/mo). Don't — these are
real apps with real workload profiles:

| Service | CPU | RAM | Disk | Why |
|---|---|---|---|---|
| Coolify admin | 0.5 vCPU share | 512MB | 2GB | Itself runs in Docker; idle most of the time |
| Gotify | 0.1 vCPU | 256MB | 200MB (SQLite) | Single Go binary |
| Memos (SQLite mode) | 0.25 vCPU | 256MB | 500MB | Single Go binary, light |
| Memos (Postgres mode) | 0.5 vCPU + $15/mo PG | 256MB | 200MB | PG host elsewhere |
| Kanboard (SQLite) | 0.1 vCPU | 256MB | 200MB | PHP-FPM, fastcgi |
| Kanboard (Postgres) | 0.25 vCPU + $15/mo PG | 256MB | 200MB | same |
| **Netdata** | **1 vCPU** | **512MB (limit)** | **4GB** | eBPF + per-second metrics = heavy |
| **Stirling-PDF** | **1 vCPU** | **1GB (JVM)** | **2GB** | Java/Headless Chrome tooling |
| Node-RED | 0.25 vCPU | 256MB | 200MB | Node, light until you wire today-* tile |

A 4GB / 2 vCPU Droplet covers all 6 services comfortably **when they're idle**.
When Stirling-PDF is rendering a 100MB PDF **and** Netdata is doing
per-second sampling under load, you can see contention. The droplet
auto-resizes down to $24/mo from $48/mo after the first month if traffic
stays low; monitor via Netdata itself.

## Service-by-service deploy plan

### Gotify
- **Build pack:** Dockerfile (point at `INAPP-Mobile/railway-gotify`)
- **Port:** 8080
- **Healthcheck:** `GET /health`
- **Volume:** `/app/data` → host volume `gotify-data`
- **DB:** SQLite in volume
- **Caveats:** Default `admin/admin` creds — see `templates/gotify.env`

### Memos
- **Build pack:** Dockerfile
- **Port:** 5230
- **Healthcheck:** `GET /health`
- **Volume:** `/var/opt/memos` (matches upstream entrypoint.sh)
- **DB choice:** SQLite for personal use; Postgres for teams.
  Spec via Coolify's "Add Database → PostgreSQL" feature (free, runs in same
  droplet). Set `MEMOS_DSN` to the Coolify-provided DATABASE_URL.

### Kanboard
- **Build pack:** Dockerfile (already patched for no-SSL in the Railway
  template; same patch carries over to Coolify's Traefik-terminated TLS).
- **Port:** 80 (matches what the patched nginx listens on)
- **Healthcheck:** `GET /healthcheck.php`
- **Volume:** `/var/www/app/data`
- **DB:** SQLite (default), switchable to Postgres

### Netdata
- **Build pack:** Dockerfile
- **Port:** 19999
- **Healthcheck:** `GET /api/v1/info`
- **Volume:** `/host` (mount the droplet's `/proc`, `/sys` so Netdata
  monitors the host **and** itself; configure via Coolify storage tab)
- **Caveat:** monitoring only works in `host` network mode. Coolify's
  default `bridge` mode will still work but stats are inside-container only.
  To monitor the host, set `Network: host` in the Coolify service config (a
  one-click toggle in the UI).
- **Auth:** `NETDATA_ENABLE_WEB_REDIRECT=false` keeps the dashboard behind
  no auth — set up Cloudflare Access rules for sub-subdomain protection OR
  enable auth via Netdata's built-in dashboard.

### Stirling-PDF
- **Build pack:** Dockerfile (long build — layer cache matters)
- **Port:** 8080
- **Healthcheck:** `GET /api/v1/info/status`
- **Volume:** `/configs` (Stirling stores custom YML config here)
- **Memory:** Set container memory limit to 1GB in Coolify UI; Java JVM
  throttles gracefully below this but PDF rendering OOMs above 700MB.
- **Auth:** Already enabled by upstream image — change
  `DEFAULT_ADMIN_PASSWORD` in `templates/stirling-pdf.env`.

### Node-RED
- **Build pack:** Dockerfile
- **Port:** 1880
- **Healthcheck:** `GET /` (the admin API is at root)
- **Volume:** `/data` (flows, settings, credentials — without this, flows
  are lost on every redeploy!)
- **Auth:** Node-RED admin auth is **disabled by default** in the upstream
  image. Enable by editing `/data/settings.js` post-deploy OR set env vars
  `NODE_RED_HTTP_NODE_AUTH_USERNAME` etc.

## Multi-tenancy (future)

To allow **external users** to one-click deploy on YOUR droplet:

1. **Option A — separate subdomains per user:** Each user gets
   `<user>.yourdomain.com`. Coolify routes via Traefik labels. Requires a
   Cloudflare Access policy so users must authenticate to see their sub.

2. **Option B — Coolify's "One-Click Services" export:** Save each
   deployment as a JSON template via Coolify UI → "Save as Template." User
   imports the JSON in their own Coolify instance. **You don't host
   anyone else's apps.** This is the safer model — preserves performance
   for your demos and charges nothing if no overlay PaaS exists.

3. **Option C — Use a marketplace partner** like Elestio, PikaPods, or
   Hostinger App Platform. They manage infrastructure; you provide the
   template definitions. Royalty per deployment.

For now, **Option A is disabled** — admin-only deploys are the sane
default. Add it later with Cloudflare Zero Trust + Coolify's user-roles
feature.

## Backups and disaster recovery

Coolify has built-in backup jobs:

```bash
# Configured in the UI → Project → Settings → Backup
# Frequency: daily
# Destination: DO Spaces
# Cost: ~$0.02/GB/month (10GB = $0.20)
```

**Critical backups:**
- Memos `/var/opt/memos` (flows + SQLite)
- Kanboard `/var/www/app/data`
- Node-RED `/data`
- Coolify itself: `docker compose exec coolify php artisan backup` (UI)

Without backups, the droplet is the only copy. A dashboard redeploy with a
typo in env vars can wipe state if you mount a fresh volume. Backups are
not optional past day 1.

## Why we DON'T use App Platform for the gallery even at $5+/mo

- **No public template gallery.** Each app is a one-off deployment.
  You (the admin) hit `deploy` from the CLI each time a user wants to use
  one. Doesn't scale beyond 1 friend.
- **No "Save as Template" inter-instance publishing.** You can't publish
  your App Platform config to a marketplace other users can browse.
- **You'd lose Traefik** (replaced by App Platform's edge proxy). Edge is
  similar in practice, but you can't proxy multiple hosts back to the same
  Droplet.
- **Cost.** $5 + $15 + $15 + $5… = $40+/mo vs $24 + $15 = $39/mo for the
  droplet model, with substantially more control.

## When to consider a buildpack instead of Dockerfile

If you later want to drop the `railway-*` repo indirection (so users see
"the upstream Dockerfile" instead of "an INAPP-deployable Dockerfile"),
switch the Coolify service build pack from `dockerfile` to `nixpacks` for
the Go-based apps (Memos, Gotify). It would skip Docker entirely and
rebuild on every commit. Don't do this unless read performance becomes a
problem — Docker layer caching is faster for repeated deploys.
