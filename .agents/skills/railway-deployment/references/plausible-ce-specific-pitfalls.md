# Plausible CE Railway Template — Pitfalls Found in Production

Session-tested failures with Plausible CE v3.2.1 on Railway (July 2026).

## 1. BASE_URL is REQUIRED (Crash if empty)

Default: `https://plausible.yourdomain.com` (placeholder is fine)

```
Runtime terminating during boot:
  ** (RuntimeError) BASE_URL configuration option required.
  /app/releases/0.0.1/runtime.exs:68
```

Empty crash. Crashes every fresh deploy until user sets a URL.

**Fix:** `BASE_URL` default placeholder set, `isOptional: false` so users see it's required.

## 2. PGDATA Path Mismatch

Fresh Postgres plugin deploys expect `/var/lib/postgresql/data` (not `/var/lib/postgresql/data/pgdata`).

```
PGDATA variable not start expected volume mount path, expected start /var/lib/postgresql/data
Please update PGDATA variable start expected volume mount path redeploy service
```

Postgres container enter crash loop. Cannot connect database, DATABASE_URL empty plausible-ce.

**Fix:** PGDATA default value must start `/var/lib/postgresql/data`.

## 3. ClickHouse Missing CLICKHOUSE_DB

CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, plus set CLICKHOUSE_DB. Missing otherwise URL trailing slash database name empty:

```
invalid URL http://plausible:password@clickhouse:8123/, no database name.
```

**Fix:** ensure clickhouse/template-vars.json includes CLICKHOUSE_DB with `plausible` default.

## 4. DATABASE_POOL_SIZE Default Too Low

Default pool size 10 auth-timing race condition "connection not available request dropped queue after 5969ms":

```
** (DBConnection.ConnectionError) connection not available request dropped queue after 5993ms.
```

**Fix:** DATABASE_POOL_SIZE default 20.

## 5. Entrypoint.sh Subcommands

v3.2.1 entrypoint.sh supports:
- `/entrypoint.sh run` (start app)
- `/entrypoint.sh db migrate` (run migrations)
- `/entrypoint.sh db create` (create db)

NOT `/entrypoint.sh createdb` or `/entrypoint.sh migrate` (earlier attempts caused `/entrypoint.sh createdb: not found`).

**Fix:** `/entrypoint.sh db migrate && /entrypoint.sh run`

## 6. Duplicate Postgres Instances

Two Postgres services pointing at different instances credential chaos, `${{Postgres.DATABASE_URL}}` resolves to stale wrong password.

**Fix:** One Postgres plugin per project. Remove `railway service delete --service <old-postgres>`.
