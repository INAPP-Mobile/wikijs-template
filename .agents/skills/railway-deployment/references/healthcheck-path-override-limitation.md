# Railway Template Deploy — healthcheckPath Pitfall

## WRONG PREVIOUS BELIEF
Earlier versions of this doc stated Railway "forces `/api/health` on ALL template-deployed services" — this was **WRONG**. The actual root cause was a `healthcheckPath: /api/health` in the **root `railway.json`** that got applied to ALL services during template generation.

## Actual Root Cause

When a root `railway.json` has `healthcheckPath` in its `deploy` block, that path gets baked into the template's `serializedConfig` and applied to **all** services — not just the root service. This is because Railway's template generator flattens the root service's deploy config across all generated services.

This session also uncovered that **`railway.json` with `"healthcheckPath": ""` (empty string) ALSO propagates** as `/api/health` because Railway treats empty string as "use framework auto-detection" which infers `/api/health` for known container images.

## The Fix

**DON'T specify `healthcheckPath` in the root `railway.json` AT ALL.** Omit the key entirely. Don't set it to `null`. Don't set it to `""`. Just remove the line.

```
// root railway.json — WRONG
{
  "deploy": {
    "healthcheckPath": "",        // STILL PROPAGATES as /api/health
    "healthcheckTimeout": 0
  }
}

// root railway.json — CORRECT
{
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
    // no healthcheckPath at all
  }
}
```

## railway.toml CONFLICT — CRITICAL

**`railway.toml` is single-service Config-as-Code.** If you have one in your repo, its `[deploy]` block's `healthcheckPath` is applied to the FIRST service Railway parses — and ignored for subsequent `[[services]]` blocks. This means:

```toml
# railway.toml — This applies /api/health to ALL services!
[deploy]
healthcheckPath = "/api/health"

[[services]]
name = "plausible"

[services.plugins.postgresql]

[[services]]
name = "clickhouse"
# This service STILL gets /api/health from [deploy] above
```

**For multi-service templates: REMOVE `railway.toml` entirely.** Use either:
- Template serializedConfig (generated via `railway templates create`)
- `.railway/railway.ts` IaC for Infrastructure-as-Code approach

## serviceInstanceUpdate DOES NOT PERSIST

```graphql
mutation {
  serviceInstanceUpdate(serviceId: "...", input: { healthcheckPath: null }) 
}
```

Returns `true` but **DOES NOT** change `deployment.meta.fileServiceManifest.deploy.healthcheckPath`. Subsequent `serviceInstanceRedeploy` calls re-create the deployment from the old config. The healthcheckPath stays `/api/health` forever.

**Workaround**: Fix the template's serializedConfig, delete the service, recreate.

## Framework Auto-Detection

When `healthcheckPath` is absent from all configs, Railway inspects the Docker image and:
- Detects the framework (Node, Python, Elixir, etc.)
- Assigns a "standard" healthcheck path
- This overrides the per-service Dockerfile HEALTHCHECK instruction

For Plausible (Elixir/BEAM on port 8000), Railway auto-detects `/api/health`. For ClickHouse, it may also detect `/api/health` because the image metadata doesn't advertise otherwise.

**Counter-intuitively, the FIX for ClickHouse is to NOT have any healthcheckPath** — Railway treats a missing healthcheckPath as "container liveness = health." The service is healthy as long as the process runs.

**Counter-intuitively, the FIX for Plausible is also to NOT have a healthcheckPath** — because the base image's `run` command does NOT auto-run migrations (see entrypoint section below). With no healthcheck, the service is considered healthy as soon as the Elixir BEAM starts, even if migrations haven't completed yet.

## Variable Override via `railway deploy`

```bash
# Override template variables during deploy:
railway deploy -t <code> -v "BASE_URL=https://example.com" -v "SECRET_KEY_BASE=..."

# Per-service override:
railway deploy -t <code> -v "plausible-ce.BASE_URL=https://..." -v "clickhouse.CLICKHOUSE_PASSWORD=..."
```

This is the ONLY way to set variables for templates that have broken serializedConfig (e.g., auto-detected `/api/health` on ClickHouse).

## `serviceCreate` Does NOT Wire Plugin Env Vars

```graphql
mutation {
  serviceCreate(input: {
    projectId: "...",
    name: "plausible-ce",
    source: { repo: "owner/repo" }
    # No env vars set! DATABASE_URL is empty!
  }) { id }
}
```

Services created manually via `serviceCreate` do NOT have plugin env vars (like `${{Postgres.DATABASE_URL}}`) resolved. The app crashes immediately.

**Use `templateDeploy` instead** — it resolves plugin references from the template's serializedConfig.

## Plausible v3.2.1 Entrypoint Facts (CRITICAL UPDATE)

- Base image: `ghcr.io/plausible/community-edition:v3.2.1`
- Entrypoint: `/entrypoint.sh` (3 subcommands: `run`, `db migrate`, `db <x>`)
- Default CMD: `run` (calls `/app/bin/plausible start`)
- ⚠️ **THE `run` COMMAND DOES NOT AUTO-RUN MIGRATIONS** — This was WRONG in earlier documentation. The app crashes with `relation "salts" does not exist` on first start.
- **REQUIRED CMD**: `CMD ["/bin/sh", "-c", "/entrypoint.sh db migrate && /entrypoint.sh run"]`
- MUST set `BASE_URL` with full `https://` scheme — `RAILWAY_PUBLIC_DOMAIN` alone lacks scheme
- MUST set `DATABASE_URL` explicitly (template deploy wires from plugin ref)

## Correct Config Structure (Verified)

```
repo/
├── railway.json          # NO healthcheckPath, NO healthcheckTimeout
├── .railway/
│   ├── railway.ts        # IaC (optional, for IaC-based deploys)
├── clickhouse/
│   ├── Dockerfile        # No HEARCHCHECK
│   ├── config.d/         # ClickHouse XML configs
│   └── railway.json      # NO healthcheckPath
└── template-vars.json    # template variable definitions
```

Result: Each service is healthy when its container runs. No healthcheck HTTP failures during initial migration.

## What Does NOT Work (Lessons)

1. **Custom migration CMD removed** — Using just `CMD ["run"]` leaves app without tables → crash
2. **Custom HEALTHCHECK path in Dockerfile** — Railway ignores Dockerfile HEARCHCHECK instruction; uses its own HTTP healthcheck
3. **Python HTTP proxy for `/api/health`** — Proxy on separate port doesn't help; proxy on main port fails because healthcheck starts before proxy process is ready
4. **`serviceInstanceUpdate` with `healthcheckPath: null`** — Returns `true` but does NOT persist on redeploy
5. **Root-level `healthcheckPath: ""`** — Empty string still causes framework auto-detection
6. **`railway.toml` in multi-service repo** — Single-service config leaks `/api/health` to all services
7. **Manual `serviceCreate` without template** — Plugin env vars not wired
8. **`railway deploy -t <code>`** — Doesn't resolve template variable syntax, creates duplicate services
9. **Missing `https://` in BASE_URL template variable** — App rejects `RAILWAY_PUBLIC_DOMAIN` alone

## Reference Template Proof

Deploy with:
```
railway deploy -t plausible-analytics-ce
```

Then inspect:
```
railway link -p <project-id>
railway variables | grep HEALTHCHECK
```

Deployment meta shows:
- clickhouse: `healthcheckPath: null` → service is healthy when running
- plausible: `healthcheckPath: /api/health` → only because the template editor set it per-service
- postgres: `healthcheckPath: null`
