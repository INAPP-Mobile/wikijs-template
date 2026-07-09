# Per-Service Raw JSON Data Reference

Extracted from live Railway project (plausible, id: 261d69ac-d21d-4bb7-af4c-506aa42ac531).

## Example capture workflow

```bash
for svc in plausible-ce postgres clickhouse; do
  echo "=== $svc ===" && railway variables --service $svc --kv 2>&1
done
```

## Field selection per service type

### Main service
Capture user-facing vars only. Skip RAILWAY_* internal vars:

| Include | Skip |
|---------|------|
| BASE_URL | RAILWAY_ENVIRONMENT |
| SECRET_KEY_BASE | RAILWAY_SERVICE_ID |
| DISABLE_REGISTRATION | RAILWAY_PROJECT_ID |
| ENABLE_EMAIL_VERIFICATION | RAILWAY_PRIVATE_DOMAIN |

### Companion service (clickhouse)
Capture ALL user-config vars. Skip RAILWAY_* internal:

| Include | Skip |
|---------|------|
| CLICKHOUSE_DB | RAILWAY_ENVIRONMENT |
| CLICKHOUSE_USER | RAILWAY_SERVICE_ID |
| CLICKHOUSE_PASSWORD | RAILWAY_PRIVATE_DOMAIN |
| PORT | RAILWAY_VOLUME_* |

### Plugin service (postgres)
Plugin manages vars internally. Deploy form show user-friendly defaults:

| User-facing var | Suggested default |
|-----------------|-------------------|
| POSTGRES_USER | "" (plugin default: postgres) |
| POSTGRES_PASSWORD | "" (plugin auto-generates) |
| POSTGRES_DB | "plausible" |
| PGDATA | "/var/lib/postgresql/data" |

## Notes
- plugin rotates POSTGRES_PASSWORD, template hardcodes → stale → auth failures.
- blank = plugin generates/uses default.
- PGDATA must match Railway volume mount path exactly `/var/lib/postgresql/data`.
- Use `${{Postgres.POSTGRES_USER}}` macros template references plugin vars; put plugin vars inside form = CRITICAL FAILURE.

---

## plausible-ce service (6 added vars, 6 RAILWAY_ auto-injected)

User-visible (non-RAILWAY_) variables:

```json
{
  "BASE_URL": "https://plausible-ce-production.up.railway.app",
  "CLICKHOUSE_DATABASE_URL": "http://plausible: clickhouse_plausible_pw_2026@clickhouse:8123/plausible",
  "DATABASE_URL": "postgresql://postgres:***@postgres.railway.internal:5432/plausible",
  "DISABLE_REGISTRATION": "false",
  "ENABLE_EMAIL_VERIFICATION": "false",
  "SECRET_KEY_BASE": "1r0csvaep4clkta54dbtel6n56kijxjgyiuc5zkpvifnjs2qlje9ryh403muwmfo",
  "RAILWAY_ENVIRONMENT": "production",
  "RAILWAY_ENVIRONMENT_ID": "35d40d99-5031-4d5c-afac-0fa49c6be20c",
  "RAILWAY_ENVIRONMENT_NAME": "production",
  "RAILWAY_PRIVATE_DOMAIN": "plausible-ce.railway.internal",
  "RAILWAY_PROJECT_ID": "261d69ac-d21d-4bb7-af4c-506aa42ac531",
  "RAILWAY_PROJECT_NAME": "plausible",
  "RAILWAY_PUBLIC_DOMAIN": "plausible-ce-production.up.railway.app",
  "RAILWAY_SERVICE_ID": "5eede556-55fe-4870-9593-2f77f350d776",
  "RAILWAY_SERVICE_NAME": "plausible-ce",
  "RAILWAY_SERVICE_PLAUSIBLE_CE_URL": "plausible-ce-production.up.railway.app",
  "RAILWAY_STATIC_URL": "plausible-ce-production.up.railway.app"
}
```

**Deploy form exposes only the 4 non-plugin vars:**

```json
{
  "BASE_URL": "",
  "SECRET_KEY_BASE": "${{secret(64)}}",
  "DISABLE_REGISTRATION": "false",
  "ENABLE_EMAIL_VERIFICATION": "false"
}
```

`CLICKHOUSE_DATABASE_URL`, `DATABASE_URL` omitted — plugins auto-inject.

## Postgres plugin service

```json
{
  "DATABASE_URL": "postgresql://postgres:***@postgres.railway.internal:5432/plausible",
  "PGDATA": "/var/lib/postgresql/data/pgdata",
  "POSTGRES_DB": "plausible",
  "POSTGRES_PASSWORD": "plausible_ce_secure_pw_2026",
  "POSTGRES_USER": "postgres"
}
```

**IMPORTANT:** These variables live **inside the Postgres service**. Deploying a project from a template that explicitly lists any of them causes:
- Empty values overriding plugin injection (when `${{Postgres.X}}` interpolation resolves incorrectly)
- Stale credentials when Railway rotates passwords
- PGDATA path mismatch crashes when user-specified value conflicts with Railway's volume mount

**Rule:** Never add `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, or `PGDATA` to `template-vars.json` or `template-editor-raw.json` when a `[[services.plugins]] name = "postgresql"` block exists in `railway.toml`.

## ClickHouse companion service

User-visible (non-RAILWAY_) variables:

```json
{
  "CLICKHOUSE_DB": "plausible",
  "CLICKHOUSE_PASSWORD": "clickhouse_plausible_pw_2026",
  "CLICKHOUSE_USER": "plausible"
}
```

Deploy form sees these (ClickHouse has **no plugin**, so all 4 are editable):

```json
{
  "CLICKHOUSE_DB": "plausible",
  "CLICKHOUSE_USER": "plausible",
  "CLICKHOUSE_PASSWORD": "clickhouse_plausible_pw_2026",
  "PORT": "8123"
}
```

## How to fetch these yourself

```bash
# Link to project
railway link --project <project-id>

# Full var dump per service (includes RAILWAY_ internals)
railway variables --service <name> --kv --json

# Filter out RAILWAY_ auto-injected vars to see user-managed ones
railway variable ls --service <name> --kv 2>&1 | grep -v '^RAILWAY_'
```

## Detecting stale credential loops

```bash
# DATABASE_URL empty or wrong password on fresh deploy = crash loop
railway logs --service plausible-ce --tail 20

# Watch for these patterns:
# "password authentication failed user \"postgres\""  → DATABASE_URL stale
# "relation \"salts\" does not exist"                → DATABASE_URL present but migrations not run
# "BASE_URL configuration option required"          → BASE_URL empty, set RAILWAY_PUBLIC_DOMAIN
# "PGDATA variable does not start with expected volume mount path" → PGDATA conflict
```
