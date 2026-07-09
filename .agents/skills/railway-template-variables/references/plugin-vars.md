# Plugin-Managed Variable Pitfalls

**Companion service (Postgres, ClickHouse) variables live INSIDE service, NOT template JSON files.** It's a trap.

## Hardcoded Credentials

`template-editor-raw.json` showing Postgres values:
```json"POSTGRES_PASSWORD": "clickhouse_plausible_pw_2026"
```
When user deploys template, this static value overrides actual rotating credential. Postgres auth fails crash loop.**Fix:**`${{Postgres.POSTGRES_PASSWORD}}`NOT hardcoded.**

## Postgres-ssl Volume Setup (Required for Template Deploy)

The `ghcr.io/railwayapp-templates/postgres-ssl:18` image does NOT self-configure on template deploy. It requires explicit volume + auth setup:

```bash
# 1. Create & attach volume (CLI does NOT do this automatically)
railway link -p <project-id> -s <postgres-service-id>
railway volume add --mount-path /var/lib/postgresql/data --json

# 2. Set auth (required — image defaults crash with "superuser password not specified")
railway variables --service <postgres-id> --set "POSTGRES_PASSWORD=<password>"
railway variables --service <postgres-id> --set "POSTGRES_USER=<user>"
railway variables --service <postgres-id> --set "POSTGRES_DB=<db>"

# 3. PGDATA — either unset, or match the mount path EXACTLY
#    PGDATA=/var/lib/postgresql/data        ✓
#    PGDATA=/var/lib/postgresql/data/pgdata ✗ (fails: "does not start with expected path")
```

**Symptom without volume:**
```
Railway volume not mounted to the correct path, expected /var/lib/postgresql/data but got
```

**Symptom without password:**
```
Error: Database is uninitialized and superuser password is not specified.
```

**Connection URL for app service:** Use internal host `<service-name>.railway.internal:5432`
```
postgresql://<user>:<password>@<service-name>.railway.internal:5432/<db>
```

## PGDATA Path Mismatch

PGDATA wrong default`/var/lib/postgresql/data/pgdata`. Fresh deploys expect`/var/lib/postgresql/data`. Postgres won't start, never generates`DATABASE_URL`.

**Fix:**Let plugin handle PGDATA, OR set exact Railway default:`/var/lib/postgresql/data``/var/lib/postgresql/data/pgdata` WRONG.

## DATABASE_URL Empty

`DATABASE_URL`shows empty`DATABASE_URL=`fresh deploys. Means Postgres plugin variables not resolving. Causes:
1. PGDATA mismatch Postgres never starts2. Reference wrong variable name (`${{Postgres.DATABASE_URL}}` is itself, not source)
3. Plugin link broken between services

**Fix:**`DATABASE_URL`built individual plugin vars:
```json
"defaultValue": "postgresql://${{Postgres.POSTGRES_USER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.POSTGRES_DB}}"```

## BASE_URL Required

Plausible crashes immediately`BASE_URL`empty. Original template had`"isOptional": true`default empty, caused crash loop.

**Fix:**`BASE_URL`required, use`${{RAILWAY_PUBLIC_DOMAIN}}`auto-set.

## Variable Reference Resolution

Plugin variables${{Postgres.*}}resolve RUNTIME fresh deploy. Not manual override.

| Variable | Source | Use In Template |
|----------|--------|-----------------|`POSTGRES_USER` | Plugin |`${{Postgres.POSTGRES_USER}}` |
|`POSTGRES_PASSWORD` | Plugin |`${{Postgres.POSTGRES_PASSWORD}}` |
|`RAILWAY_PRIVATE_DOMAIN` | Plugin |`${{Postgres.RAILWAY_PRIVATE_DOMAIN}}` |
|`POSTGRES_DB` | Plugin |`${{Postgres.POSTGRES_DB}}` |
|`DATABASE_URL` | Plugin (generated) | `${{Postgres.DATABASE_URL}}` NOT hardcoded|

## Companion Service Definition (railway.toml)

```toml
[[services]]
 id = "plausible-ce"
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
 mount_path = "/var/lib/clickhouse"```

## Two-File Sync

`template-vars.json`(source truth) and`template-editor-raw.json`must stay same keys. Pipeline auto-generates one from other.

When manually editing both, verify:
```bash
python3 -c "import json; d1=json.load(open('template-vars.json')); d2=json.load(open('template-editor-raw.json')); print('OK' if set(d1)==set(d2) else 'MISMATCH')
"```

## Pre-Publish Checklist

- [ ] No hardcoded credentials (passwords, domains)
- [ ]`BASE_URL`uses `${{RAILWAY_PUBLIC_DOMAIN}}`required
- [ ]`DATABASE_URL`built `${{Postgres.*}}`plugin vars
- [ ]`CLICKHOUSE_*`vars use `${{clickhouse.*}}`references
- [ ] No`PGDATA`override (or exact Railway default)
- [ ] Both JSON files same keys
- [ ] Test deploy: all services Online
- [ ] Test deploy:`DATABASE_URL`not empty