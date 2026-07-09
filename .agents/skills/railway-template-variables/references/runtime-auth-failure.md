# Runtime Credential Auth Failures

Common auth failure modes when pass credentials manually vs injecting plugin vars.

## Stale Postgres Password

**Symptom:**
```
FATAL 28P01 (invalid_password) password authentication failed user "postgres"
```

**Root cause:** Railway Postgres plugin auto-rotates password each deployment. If template hardcodes password or uses stale `DATABASE_URL` from project vars, auth fails after rotation.

**Fix:** Use `${{Postgres.DATABASE_URL}}` reference instead of `${{Postgres.POSTGRES_USER}}`+`${{Postgres.POSTGRES_PASSWORD}}` composition, OR set a fixed password via `railway variable set POSTGRES_PASSWORD=...` on the Postgres service itself.

## ClickHouse Auth Failure

**Symptom:**
```
Code: 516. DB::Exception: plausible: Authentication failed: password incorrect, or there is no user
```

**Root cause:** ClickHouse service missing `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, or `CLICKHOUSE_DB` vars. Default user `default` may not exist if `CLICKHOUSE_SKIP_USER_SETUP=1` was removed without adding replacement user vars.

**Fix:** Set these on ClickHouse service:
- `CLICKHOUSE_DB` = `plausible`
- `CLICKHOUSE_USER` = `plausible`
- `CLICKHOUSE_PASSWORD` = `${{secret(24)}}`

## Connection Pool Timeout

**Symptom:**
```
connection not available and request dropped from queue after 5969ms
```

**Root cause:** Pool size too small (default 10) for auth handshake latency, OR credentials failing in retry loop.

**Fix:** Bump pool size via `DATABASE_POOL_SIZE=20` project var.

## Duplicate Companion Services

**Plausible CE crashed with wrong-stale Postgres credential pointing duplicate service.**

**Root cause:** Two Postgres services exist (e.g., `Postgres` + `Postgres-Q6IU`). Template's `${{Postgres.DATABASE_URL}}` resolves to whichever one linked as plugin.

**Fix:** Remove duplicate service, ensure only ONE companion service per plugin name referenced.

---

## Quick Reference: entrypoint.sh v3.2.1

```
/entrypoint.sh run                  → start server
/entrypoint.sh db migrate           → run migrations  
/entrypoint.sh db create            → create database (Plausible CE handles internally)
```
