---
type: reference
title: "Stale Credentials After Plugin-Backed Redeploys"
---

# Stale Credentials After Plugin-Backed Redeploys

## Symptom

Service crashes auth failures immediately after successful build:

```FATAL 28P01 (invalid_password) password authentication failed for user "postgres"
Ch.Error Code: 516 AUTHENTICATION_FAILED
```

## Root Cause

Railway plugin services (Postgres, MySQL, ClickHouse via `[[services.plugins]]` in `railway.toml`) auto-rotate passwords on each redeploy.

**Why this bites:**
1. Consumer service gets injected `DATABASE_URL` at first deploy with current plugin password.
2. Next redeploy → plugin rotates password → consumer's var has stale password.
3. Plausible boots tries stale password → `FATAL 28P01` → crash loop.

## Confirmed Additional Triggers Found Session

1. **Duplicate service confusion**: Two `Postgres` services creates (`Postgres` + `Postgres-Q6IU`) makes `${{Postgres.DATABASE_URL}}` macro resolve unpredictably empty.
2. **Template-baked manual overrides**: Manually setting `DATABASE_URL` user project bakes into template → future users inherit stale literal string.
3. **`${{...}}` interpolation produces empty strings**: When duplicate services exist `${{Postgres.DATABASE_URL}}` expands `postgresql://postgres:@:/plausible` (empty host/password).

## Diagnosis

```bash
railway variables --service <app> --kv | grep DATABASE_URL
```

Empty output → macro resolution broken.

## The Rule

**DO NOT** put these `template-vars.json`:
- `DATABASE_URL`
- `CLICKHOUSE_DATABASE_URL`
- `POSTGRES_PASSWORD`
- `POSTGRES_USER`
- `POSTGRES_DB`
- `PGDATA`

**EXCEPTION required** ClickHouse companion vars:
- `CLICKHOUSE_DB`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD` needed (defaults `${{secret(N)}}`)

Let plugin auto-inject everything.

## Fix Actions

1. Remove duplicate services: `railway service delete --service <dupe> --yes`
2. Remove manual overrides template JSON
3. Republish template

## Build-only `${{Postgres.DATABASE_URL}}` Defense-In-DepthIf `${{Postgres.DATABASE_URL}}` still empty duplicate services gone, build from component vars:```json
"DATABASE_URL": {
  "defaultValue": "postgresql://${{Postgres.POSTGRES_USER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.POSTGRES_DB}}"
}
```

This not needed single Postgres service project.
