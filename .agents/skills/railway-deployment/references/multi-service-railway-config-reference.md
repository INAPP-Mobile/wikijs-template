# Multi-Service Railway Config — Verified Pattern

Verified working 2026-07-08 by deploying `plausible-analytics-ce` reference template and reproducing with own repo (`INAPP-Mobile/railway-plausible`).

## Directory Structure

```
repo/
├── railway.json          # root service ONLY (no healthcheckPath)
├── Dockerfile            # root service build
├── clickhouse/
│   ├── Dockerfile        # ClickHouse with custom config
│   ├── railway.json      # ClickHouse-specific deploy config
│   ├── config.d/         # ClickHouse config XMLs
│   └── users.d/          # ClickHouse user overrides
```

## File Contents

### root `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```
NO `healthcheckPath` — Railway does not force a path when none is set.

### `clickhouse/railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```
NO healthcheckPath. ClickHouse is considered healthy when the process starts.

### `clickhouse/Dockerfile`
```dockerfile
FROM clickhouse/clickhouse-server:24.12-alpine
COPY config.d/ /etc/clickhouse-server/config.d/
COPY users.d/  /etc/clickhouse-server/users.d/
```

### `clickhouse/config.d/railway-listen.xml`
```xml
<clickhouse>
    <listen_host>::</listen_host>
</clickhouse>
```

### `clickhouse/config.d/low-resources.xml`
```xml
<clickhouse>
    <mark_cache_size>524288000</mark_cache_size>
</clickhouse>
```

## Volume Mounts

Configure in template editor raw JSON:
- ClickHouse: `/var/lib/clickhouse` on `clickhouse-volume`
- Postgres: `/var/lib/postgresql/data` on `postgres-volume`

## Variable Injection (Template Editor)

| Service | Variable | Value |
|---------|----------|-------|
| Postgres | `POSTGRES_PASSWORD` | `${{secret(16)}}` |
| Postgres | `POSTGRES_USER` | `plausible` |
| Postgres | `POSTGRES_DB` | `plausible_db` |
| ClickHouse | `CLICKHOUSE_USER` | `plausible` |
| ClickHouse | `CLICKHOUSE_PASSWORD` | `${{secret(16)}}` |
| ClickHouse | `CLICKHOUSE_DB` | `plausible_events_db` |
| Plausible | `BASE_URL` | `${{RAILWAY_PUBLIC_DOMAIN}}` |
| Plausible | `SECRET_KEY_BASE` | `${{secret(64)}}` |
| Plausible | `DATABASE_URL` | `postgresql://plausible:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.PRIVATE_DOMAIN}}:5432/plausible_db` |
| Plausible | `CLICKHOUSE_DATABASE_URL` | `http://plausible:${{ClickHouse.CLICKHOUSE_PASSWORD}}@${{ClickHouse.PRIVATE_DOMAIN}}:8123/plausible_events_db` |
| Plausible | `DISABLE_REGISTRATION` | `false` |
| Plausible | `ENABLE_EMAIL_VERIFICATION` | `false` |

## Entrypoint Inspection Technique

When using an unknown base image, inspect its entrypoint BEFORE writing CMD:
```bash
podman run --rm --entrypoint /bin/sh <image> -c "cat /entrypoint.sh"
```
For `plausible/community-edition:v3.2.1`:
```sh
#!/bin/sh
set -e

if [ "$1" = 'run' ]; then
    exec /app/bin/plausible start   # auto-runs migrations
elif [ "$1" = 'db' ]; then
    exec /app/"$2".sh
else
    exec "$@"
fi
```
Key insight: `run` already runs migrations via Elixir release. Custom `db migrate && run` is unnecessary.

## Filesystem Permissions (Git)

Config files committed to Git retain their local mode. ClickHouse reads config as a non-root user — files MUST be 644 (world-readable), not 600:
```
644 config.d/*.xml   # correct
600 config.d/*.xml   # causes "Access to file denied" crash
```

## Procedure to Create Template

1. **Build services in repo** — ensure Dockerfile and railway.json files are correct per-service
2. **Test deploy each service:**
   ```bash
   railway up . --new --name <svc-name> -y   # creates standalone project
   railway status                             # verify ONLINE
   ```
3. **Create combined test project:**
   ```bash
   cd repo/ && railway up . --path-as-root --project <test-project-id> -e production -y
   cd repo/clickhouse/ && railway up . --path-as-root --project <test-project-id> --service <new-svc-id> -e production -y
   ```
4. **Generate template:**
   ```bash
   railway templates create --project <test-project-id> --json
   ```
5. **If template has wrong healthcheck config** — delete and regenerate. No `templateUpdate` mutation exists.

## Gotchas

- `railway templates create` fails if any service source cannot be extracted
- Test each service individually before combining into multi-service project
- No `templateUpdate` mutation — must delete and regenerate to fix
</python|bout `serviceInstanceUpdate` with `healthcheckPath` — returns `true` but does NOT change `deployment.meta`
- Railway ignores Dockerfile HEALTHCHECK; uses its own HTTP healthcheck against deploy config</｜DSML｜parameter>