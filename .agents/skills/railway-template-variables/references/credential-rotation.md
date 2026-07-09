# Railway Template Variable Pitfalls — Credential Rotation & Plugin Vars

## The Time-Bomb Problem

Railway Postgres plugin **auto-rotates passwords** on every deployment. If you hardcode a password:

```
DATABASE_URL=postgresql://postgres:HARDCODED$PWD@postgres.railway.internal:5432/db
```

Then redeploy, the plugin changes `POSTGRES_PASSWORD` to a new random value → `DATABASE_URL` is stale → auth failures → crash loop. Every time you check, the password has rotated again.

### The Only Safe Pattern

**Never hardcode password-bearing values in the deploy form.** Always reference plugin variables dynamically:

```json
"DATABASE_URL": {
  "value": "${{Postgres.DATABASE_URL}}"
}
```

Or construct from plugin vars:

```json
"DATABASE_URL": {
  "value": "postgresql://${{Postgres.POSTGRES_USER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.POSTGRES_DB}}"
}
```

These resolve **live at deploy time** — always fresh.

## Service Structure Pattern (Confirmed Working)

### 1. Define services in `railway.toml`

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[[services]]
id = "plausible"
name = "Plausible CE"
builder = "DOCKERFILE"
dockerfile_path = "Dockerfile"

[[services.plugins]]
name = "postgresql"

[[services]]
id = "clickhouse"
name = "ClickHouse"
builder = "DOCKERFILE"
dockerfile_path = "clickhouse/Dockerfile"

[[services.plugins]]
name = "volume"
mount_path = "/var/lib/clickhouse"
```

### 2. Define companion references in `companion-mapping.json`

```json
{
  "postgres": {
    "DATABASE_URL": "DATABASE_URL"
  },
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 3. Define variables split by service

**`template-vars.json`** — main app variables:

```json
{
  "BASE_URL": { "defaultValue": "", "isOptional": true },
  "SECRET_KEY_BASE": { "defaultValue": "${{secret(64)}}", "isOptional": false },
  "DATABASE_URL": { "defaultValue": "${{Postgres.DATABASE_URL}}", "isOptional": false },
  "CLICKHOUSE_DATABASE_URL": {
    "defaultValue": "http://${{clickhouse.CLICKHOUSE_USER}}:${{clickhouse.CLICKHOUSE_PASSWORD}}@clickhouse:8123/${{clickhouse.CLICKHOUSE_DB}}",
    "isOptional": true
  }
}
```

**`clickhouse/template-vars.json`** — ClickHouse reference vars (must use Railway service-name prefix):

```json
{
  "CLICKHOUSE_DB": { "defaultValue": "plausible", "isOptional": true },
  "CLICKHOUSE_USER": { "defaultValue": "plausible", "isOptional": false },
  "CLICKHOUSE_PASSWORD": { "defaultValue": "${{secret(24)}}", "isOptional": false }
}
```

### 4. Sync files

```bash
editor = json.load(open("template-vars.json"))
raw = {k: {"value": v.get("defaultValue", ""), "description": v.get("description", "")} for k, v in editor.items()}
json.dump(raw, open("template-editor-raw.json", "w"), indent=2)
```

Same for clickhouse editor.

## Pitfalls We Hit (And Fixed)

### Pitfall 1: Deployment fails with `pg_hba.conf` auth error
**Sym`/`FATAL 28P01 invalid_password`. password keeps changing every deploy.
**Fix:** Use `${{Postgres.DATABASE_URL}}` (dynamic plugin reference), never hardcoded password.

### Pitfall 2: Postgres crashes with `PGDATA volume path mismatch`
**Symptom:** `PGDATA variable does not start with expected volume mount path, expected /var/lib/postgresql/data`.
**Root cause:** Template captured an override from a project where PGDATA was customized (e.g., `/var/lib/postgresql/data/pgdata`). Railway's default is `/var/lib/postgresql/data`. The template overrode the plugin's default and is now wrong for fresh deploys.
**Fix:** Remove `PGDATA` from template entirely. Let Railway plugin manage it.

### Pitfall 3: Empty DATABASE_URL on fresh deploy
**Symptom:** `DATABASE_URL=` (empty) in the deployed project.
**Root cause:** Template captured an explicit empty string for `DATABASE_URL` from the original project, which Railway overwrote on subsequent deploys. Fresh template users get the empty default.
**Fix:** Use `${{Postgres.DATABASE_URL}}` (never hardcoded). Captured default must NOT be empty — deploy form should receive value from plugin interpolation at provision time.

### Pitfall 4: Stale hardcoded passwords in template-editor-raw.json
**Symptom:** Template deployed with clickhouse password from original project → auth failure on fresh deploy (different password).
**Fix:** Use `$${{secret(24)}}` for all user-visible secrets (auto-generated per deploy) OR reference plugin vars.

## Critical: Capture-Default vs. Provision-Time

| Approach | Safe? | Notes |
|----------|-------|-------|
| Capture current value → hardcode | **NEVER** | Rotates → stale fresh deploys |
| `${{Postgres.DATABASE_URL}}` | YES | Dynamic plugin reference |
| `${{secret(64)}}` | YES | Auto-generated fresh each deploy |
| Explicit empty string `""` | Never | Fresh deploy may require non-empty |

## Verification Steps

1. **Create template from project:** `railway templates create --project <id>`
2. **Publish (publishes current project state as template):** `railway templates publish <code> --category "Analytics" --description "..." --readme-file README.md`
3. **Deploy fresh:** Use the URL `https://railway.com/deploy/<code>` in a new browser/account OR `railway deploy --template <code>` — but deploy requires TTY (needs interactive console). Browser test is reliable.
4. **Verify services online:** `railway status` from the new project
5. **Check vars populated:** `railway variables --service <main-app> --kv`
6. **Confirm DATABASE_URL not empty:** must show full connection string
7. **Check app boots:** `railway logs --service <main-app>` — should not show auth/PGDATA/BASE_URL errors

## Quick Fix Script for Postgres Plugin Templates

```bash
# Find the plugin-injected values (run these before authoring template-vars.json)
railway variables --service <app> --kv | grep -E '^(BASE_URL|DATABASE_URL|CLICKHOUSE|SECRET|DISABLE_|ENABLE_)=' 
# Then use plugin references in template-vars.json, never hardcoded values
```

## Legal prefix rules

- Service name in `${{...}}` prefix must match the Railway internal service name (the one you get from `railway service ls`)
- **ClickHouse default service name is `ClickHouse`** (note capital H) but Railway internally assigns **`clickhouse`** lowercase in var interpolation (re-confirmed by working `${{clickhouse.CLICKHOUSE_USER}}`). If you see `ClickHouse` failing, try lowercase. The plugin-mapping file specifies all lowercase keys (`"clickhouse":`), and that's what works.
- Postgres plugin: **`Postgres`** (with capital P) — confirmed working `${{Postgres.DATABASE_URL}}`.
