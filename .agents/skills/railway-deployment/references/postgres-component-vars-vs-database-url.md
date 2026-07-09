---
type: reference
title: "Plugin Credential Desync"
---

# Plugin Credential Desync — When DATABASE_URL Gets Empty/Stale

## Symptom

- `railway variables --service <app> --kv | grep DATABASE_URL` returns `DATABASE_URL=` (empty)
- Logs show `FATAL 28P01 (invalid_password)`
- Post-crash follow-up orth:`postgresql://postgres:@:/plausible` (empty host, empty password)

## Root Causes (Session-Learned)

### Cause 1: Duplicate Services

Two Postgres instances same project (`Postgres` + `Postgres-Q6IU`) `${{Postgres.DATABASE_URL}}` macro resolves unpredictable — sometimes empty, sometimes wrong service. Easy leftover failed template deploys create duplicates.

```bash
# Check duplicates
railway service ls
# delete stale ones
railway service delete --service <dupe> --yes
```

### Cause 2: Template-Baked Stale Overrides

Manually setting `DATABASE_URL`, `POSTGRES_PASSWORD`, etc. source project gets baked into template `defaultValue` Future users inherit stale literal string.

### Cause 3: interpolation happens at template publish time

Template interpolation happens at template publish time, not deploy time. So placeholder `${{Postgres.DATABASE_URL}}` stale first-values.

## Rule

**DO NOT** put these in template-vars.json (let plugin auto-inject at deploy time):
- `DATABASE_URL`
- `CLICKHOUSE_DATABASE_URL`
- `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`
- `PGDATA`

**EXCEPTION:** ClickHouse companion vars requiring explicit entry because plugin not auto-inject set defaults:
- `CLICKHOUSE_DB`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`

## Component-Vars Recipe (Single Postgres Service Only)

```json
{
  "DATABASE_URL": {
    "defaultValue": "postgresql://${{Postgres.POSTGRES_USER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.POSTGRES_DB}}"
  }}
```

Each piece resolves independently deploy, bypass macro-cache bugs. Stricter variant also resilient duplicate service edge cases.

## Verification

After every templated deploy:
```bash
railway variables --service <app> --kv | grep DATABASE_URLrailway status
```

Non-empty + all services Online → success.
