# Plausible CE v3.2.1: Entrypoint Subcommands, Volume Setup, Dockerfile Paths

**Symptom**: `plausible-ce: Crashed` restart loop, immediate crash.

## Phase 1 — malformed CMD (syntax)

```
/entrypoint.sh: exec: line 10: createdb: not found
/entrypoint.sh: exec: line 10: /entrypoint.shrun: No such file or directory
```

**Root cause:** CMD was missing `&&` between chain elements. Missing operators inside JSON array strings collapse visually in terminals.

**Verification**:
```bash
python3 -c "print(repr(open('Dockerfile').read()))"  # raw bytes reveals truth
cat Dockerfile | sed -n '/CMD/p' | grep -c '&&'     # count = chain length - 1
```

## Phase 2 — wrong assumption about entrypoint.sh subcommands

After adding `&&`, tried `/entrypoint.sh createdb && /entrypoint.sh migrate && /entrypoint.sh run` → `exec: line 10: createdb: not found`.

**Actual entrypoint.sh** (v3.2.1, verified via `podman run --rm --entrypoint /bin/sh ghcr.io/plausible/community-edition:v3.2.1 -c "cat /entrypoint.sh"`):

```sh
#!/bin/sh
set -e
if [ "$1" = 'run' ]; then
      exec /app/bin/plausible start
elif [ "$1" = 'db' ]; then
      exec /app/"$2".sh
else
      exec "$@"
fi
exec "$@"
```

Subcommands:
- `run` → starts the release (no migrations!)
- `db <name>` → runs `/app/<name>.sh` (e.g., `db migrate` → `/app/migrate.sh`)

**Correct CMD:**
```dockerfile
CMD ["/bin/sh", "-c", "/entrypoint.sh db migrate && /entrypoint.sh run"]
```

**Pitfall Update (2026-07-08):** Earlier versions claimed `run` does NOT auto-run migrations. This was WRONG. The Elixir release `bin/plausible start` called by `run` DOES apply pending migrations at startup. The custom `CMD ["/bin/sh", "-c", "/entrypoint.sh db migrate && /entrypoint.sh run"]` is redundant but harmless — both paths apply migrations.

**Simplest Dockerfile that works:**
```dockerfile
FROM ghcr.io/plausible/community-edition:v3.2.1

ENV PORT=8000
```

No custom CMD needed. The base image's default `run` command handles migrations and starts the app.

## Phase 3 — postgres-ssl image volume setup (required for DATABASE_URL)

Railway postgres template needs explicit setup or fails with:
```
Railway volume not mounted to the correct path, expected /var/lib/postgresql/data but got
Error: Database is uninitialized and superuser password is not specified.
```

**Fix sequence:**
```bash
# 1. Create volume
railway link -p <project> -s <postgres-service-id>
railway volume add --mount-path /var/lib/postgresql/data --json

# 2. Set auth env vars (required — no defaults)
railway variables --service <postgres-id> \
  --set "POSTGRES_PASSWORD=railway" \
  --set "POSTGRES_USER=railway" \
  --set "POSTGRES_DB=railway"

# 3. PGDATA coordination
# Either unset, or match exactly: PGDATA=/var/lib/postgresql/data
# NO trailing subpaths (e.g., /var/lib/postgresql/data/pgdata fails)

# 4. Get connection URL for the app service
# Internal host: <service-name>.railway.internal, port 5432
railway variables --service <app-id> \
  --set "DATABASE_URL=postgresql://railway:railway@<postgres-service-name>.railway.internal:5432/railway"
```

**Why:** postgres-ssl image does not self-configure on template deploy. `railway deploy -t <code>` does NOT create volumes — only the editor UI flow does.

## Phase 4 — Dockerfile COPY path vs rootDirectory

When `source.rootDirectory = "clickhouse"` in template editor JSON, the build context IS that directory. COPY paths must be **relative to the rootDirectory**, not include the prefix:

```dockerfile
# WRONG (double-nested):
COPY clickhouse/logs.xml /etc/clickhouse-server/config.d/logs.xml

# RIGHT (relative to clickhouse/):
COPY logs.xml /etc/clickhouse-server/config.d/logs.xml
```

**Symptom:** `failed to compute cache key: ... "/clickhouse/default-profile-low-resources-overrides.xml": not found`

## Phase 5 — CLI deploy creates duplicate services with no volumes

`railway deploy -t <code>` does NOT reuse existing services. It creates NEW services with randomized suffixes (`clickhouse-bHKB`, `plausible-ce-0_76`, `plausible-postgres-r8oJ`) and does NOT:
- Resolve `${{...}}` template var syntax
- Create volume mounts
- Set POSTGRES_PASSWORD

**Use case:** Only for validating the Dockerfile source builds correctly. NOT for template variable testing.

To remove duplicates: `railway service delete -s <id> -y`

## Phase 6 — healthcheck timeout too low for slow-starting services

ClickHouse (Alpine, low-resource config) can take >90s on first start. Railway default `healthcheckTimeout: 60` + `restartPolicyMaxRetries: 5` fails the deployment.

**Fix:** Increase `restartPolicyMaxRetries` to 10-15. Do NOT add `healthcheckPath` — Railway does not force `/api/health` when no path is set, and the service is considered healthy when its process starts.

```json
"deploy": {
  "restartPolicyMaxRetries": 10,
  "restartPolicyType": "ON_FAILURE"
}
```

**Counter-intuitive finding (2026-07-08):** Adding `"healthcheckPath": "/ping"` to ClickHouse makes things WORSE if set at root level (propagates to all services). The reference template (`agafonovim/railway-templates`) uses NO `healthcheckPath` anywhere and all services deploy successfully.

## General rule

When building `FROM <upstream>` Dockerfiles:
1. **Inspect the entrypoint** before assuming subcommands: `podman run --rm --entrypoint /bin/sh <image> -c "cat /entrypoint.sh"`
2. **Verify COPY paths** match the actual build context (rootDirectory in template, or repo root for plain services)
3. **Test the CMD chain** with `repr()` — never trust `cat` for operator visibility
