# Plugin-Managed Variables: Do NOT Add These to Template

Railway plugin services (Postgres, MySQL, ClickHouse via `[[services.plugins]]` in `railway.toml`) inject these variables directly. Adding them to `template-vars.json` creates conflicts.

## Never Template

| Variable | Where it lives | Conflict if templated |
|---|---|---|
| `POSTGRES_USER` | Postgres plugin service | plugin overwrites template value, template re-applies stale default |
| `POSTGRES_PASSWORD` | Postgres plugin service | password auto-rotates on deploy; template hardcodes the stale one |
| `POSTGRES_DB` | Postgres plugin service | differs by project; template value overrides per-project expectation |
| `PGDATA` | Postgres plugin service | plugin sets `/var/lib/postgresql/data`; template often has `/var/lib/postgresql/data/pgdata` — mismatch crashes boot |
| `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DB` | ClickHouse companion service | auto-rotate; template hardcoding kills fresh deploys |

## Correct Pattern (Reference, Don't Set)

```json
{
  "DATABASE_URL": {
    "defaultValue": "${{Postgres.DATABASE_URL}}",
    "isOptional": false
  }
}
```

This single macro re-resolves at every deploy — always current, never stale.

## What "Fresh Project" Verification Catches (That Source Project Won't)

The source project where the template was developed has manual overrides from debugging:
- Manually-set `POSTGRES_PASSWORD` (plugin ignored)

- Manually-set `BASE_URL` (var populated)

- Manually-running fixes that masked template bugs

A fresh project gets **only** what the template says. If template-vars.json has no `BASE_URL` default, fresh deploy crashes with "BASE_URL configuration option required". If it has `PGDATA` with wrong path, Postgres crashes with "PGDATA variable not start with expected volume mount path".

**Rule**: `railway templates publish` → `railway deploy` new project → check `railway status` + `railway logs` + `railway variables`. No exceptions.
