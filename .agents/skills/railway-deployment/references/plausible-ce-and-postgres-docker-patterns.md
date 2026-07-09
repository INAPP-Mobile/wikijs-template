# Railway Postgres-SSL Image Requirements

## Image: `ghcr.io/railwayapp-templates/postgres-ssl:18`

### Required Configuration

Railway's managed Postgres image has strict requirements that are NOT documented in the public repo:

| Setting | Required Value | Why |
|---------|---------------|-----|
| Volume mount path | `/var/lib/postgresql/data` | Hardcoded expectation |
| `POSTGRES_PASSWORD` | Non-empty string | "Database is uninitialized and superuser password is not specified" |
| `PGDATA` | NOT set (or exactly `/var/lib/postgresql/data`) | Crash if set to subpath like `/var/lib/postgresql/data/pgdata` |

### Deployment Sequence for Postgres via CLI

```bash
# 1. Create volume mount FIRST
railway volume add --service <pg-service-id> --mount-path /var/lib/postgresql/data --json

# 2. Set password
railway variables --service <pg-service-id> --set "POSTGRES_PASSWORD=railway" --set "POSTGRES_USER=railway" --set "POSTGRES_DB=railway"

# 3. Redeploy to apply
railway service redeploy -s <pg-service-id> -y
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Railway volume not mounted to the correct path, expected /var/lib/postgresql/data" | No volume mount created | `railway volume add --service <id> --mount-path /var/lib/postgresql/data` |
| "Database is uninitialized and superuser password is not specified" | `POSTGRES_PASSWORD` not set | `--set "POSTGRES_PASSWORD=<value>"` |
| "PGDATA variable does not start with the expected volume mount path" | `PGDATA` set to subpath | Remove `PGDATA` variable entirely |

### Template SerializedConfig for Postgres

```json
{
  "icon": "https://devicons.railway.app/i/postgresql.svg",
  "name": "plausible-postgres",
  "deploy": {
    "startCommand": null,
    "healthcheckPath": null,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "source": {
    "image": "ghcr.io/railwayapp-templates/postgres-ssl:18"
  },
  "variables": {
    "POSTGRES_PASSWORD": {"value": "${{secret(16)}}", "description": "Postgres password"},
    "POSTGRES_USER": {"value": "plausible", "description": "Postgres user"},
    "POSTGRES_DB": {"value": "plausible", "description": "Postgres database"}
  }
}
```

⚠️ Railway's template deploy does NOT auto-create volume mounts for database images — the mount must exist BEFORE the service is created. When deploying from a template, the Postgres service will fail until the user manually adds a volume mount via CLI or UI unless the volume was pre-created in the template source project AND serializes correctly.

## Volume Creation via API

```graphql
mutation {
  volumeCreate(input: {
    projectId: "...",
    environmentId: "...",
    serviceId: "...",
    mountPath: "/var/lib/postgresql/data"
  }) {
    id
  }
}
```

⚠️ `volumeCreate` may not exist as a standalone mutation — verify via introspection. Alternative: `railway volume add --service <id> --mount-path /var/lib/postgresql/data`

---

### Lost+Found Gotcha — Empirically Verified 2026-07-08

Volume mount path `/var/lib/postgresql/data` WILL fail initdb because ext4 lost+found is non-empty. The image expects PGDATA exactly at this path (no subpath workaround), and lost+found is unavoidable when Railway formats a new volume.

**Root cause:**
- Railway creates new volumes by running `mke2fs` on them, which automatically creates a `lost+found/` directory at the volume root
- When the volume is mounted at `/var/lib/postgresql/data`, this `lost+found/` manifests as `/var/lib/postgresql/data/lost+found`
- Postgres `initdb` (in both `postgres:16-alpine` and `postgres-ssl:18` entrypoints) refuses to initialize a PGDATA directory that has entries but no `PG_VERSION` file. Concretely, with only `lost+found/` present, `initdb` errors with `error: directory "/var/lib/postgresql/data" exists but is not empty` — because Postgres treats "entries without `PG_VERSION`" as "not an initialized cluster, but too dirty to init fresh."
- This error appears AFTER the PGDATA path-mismatch check passes: the subsequent `initdb` step reports the lost+found collision

**Why no subpath workaround:**
- The postgres-ssl:18 image's custom entrypoint checks that `PGDATA` starts with the expected volume mount path `/var/lib/postgresql/data` and refuses subpaths
- Subpath workarounds like `PGDATA=/var/lib/postgresql/data/pgdata` crash with `PGDATA variable does not start with the expected volume mount path`
- Re-mounting the volume at a different path (e.g., `/pgdata`) doesn't help: PGDATA would need to start with that path, but the postgres-ssl:18 image's hardcoded check rejects anything other than `/var/lib/postgresql/data`
- Each Railway volume is created with the same lost+found default — there is no mount path that avoids this

**Why Path B (sibling service) is the only reliable fix:**
- A sibling service using the upstream `postgres:16-alpine` image (NOT `postgres-ssl:18`) uses the standard Postgres `docker-entrypoint.sh` (the upstream `postgres` library's entrypoint, not Railway's wrapper). The upstream entrypoint does NOT enforce `PGDATA` start-with-mount-path — so a sibling service can mount its volume at a parent path (e.g. `/var/lib/postgresql`) with `PGDATA=/var/lib/postgresql/data`. That geometry places the volume's `lost+found/` outside PGDATA, where initdb sees an empty dir and proceeds. postgres-ssl:18 forbids this geometry with its strict path-prepend check, forcing the volume to mount at exactly `/var/lib/postgresql/data` and trapping `lost+found/` inside PGDATA
- The sibling service pattern lets you set `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` as **literal** env vars in the template's per-service JSON (which marketplace deploys CAN read)
- Plausible CE can then reference `postgresdb.railway.internal` with a fully literal `DATABASE_URL`, eliminating the `${{Postgres.*}}` empty-resolution risk AND the lost+found init blocker
- See `references/config-as-code-vs-iac.md` for the IaC pattern (`.railway/railway.ts`) needed to encode the sibling service + volume

**Verified on:** Railway project `lavish-beauty` (ID `ad967011-0a84-45d4-a039-d46f847ef2a0`), production env, 2026-07. Setting `PGDATA=/var/lib/postgresql/data` via `railway variables set -s Postgres PGDATA=/var/lib/postgresql/data` passed the path-mismatch check, then initdb failed with the lost+found error on a fresh volume that had been auto-provisioned by the marketplace template deploy.

---

# Plausible Community Edition Docker Entrypoint

## Image: `ghcr.io/plausible/community-edition:v3.2.1`

### Entrypoint Behavior

```bash
$ podman run --rm --entrypoint /bin/sh plausible/community-edition:v3.2.1 -c "cat /entrypoint.sh"
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

### Available Commands

| Command | What it does | When to use |
|---------|-------------|-------------|
| `run` | Starts the Plausible server (`/app/bin/plausible start`) | Runtime |
| `db migrate` | Runs `/app/migrate.sh` to apply database migrations | First boot / schema updates |
| `db <anything>` | Executes `/app/<anything>.sh` | Arbitrary db scripts |
| `exec "$@"` | Falls through to shell exec | Catch-all |

### Correct CMD for Railway

```dockerfile
FROM ghcr.io/plausible/community-edition:v3.2.1

ENV PORT=8000

# Run database migrations then start the release
# entrypoint.sh: "db migrate" runs /app/migrate.sh, "run" starts /app/bin/plausible
CMD ["/bin/sh", "-c", "/entrypoint.sh db migrate && /entrypoint.sh run"]
```

Theirarchy: with custom migration CMD. Plausible's Elixir release does NOT automatically migrate — app crashes with `relation "salts" does not exist` on first start unless explicit migration is run.

### Wrong CMDs (will fail)

| Wrong CMD | Failure |
|-----------|---------|
| `CMD /entrypoint.sh migrate` | `exec: line 10: migrate: not found` |
| `CMD /entrypoint.sh start` | `exec: line 10: start: not found` |
| `CMD /entrypoint.sh run` | Works but NO migrations - app crashes with `relation "salts" does not exist` |
| Custom `CMD ["/bin/sh", "-c", "bin/plausible eval 'Plausible.Release.migrate' && bin/plausible start"]` | Path wrong, release binary not at that location |

### Application Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `BASE_URL` | YES | — | Must start with `http` or `https` |
| `SECRET_KEY_BASE` | YES | — | 64-char random string |
| `DATABASE_URL` | YES | — | PostgreSQL connection string |
| `DISABLE_REGISTRATION` | no | `false` | Set `true` to disable signup |
| `CLICKHOUSE_DATABASE_URL` | YES | — | ClickHouse HTTP URL |
| `PORT` | no | `8000` | Railway injects its own |

### Minimal Working Dockerfile (Verified)

⚠️ **The base image's `run` command does NOT auto-run migrations.** This was incorrectly documented in earlier versions. While the official reference template (`agafonovim/railway-templates`) uses the minimal pattern, it works because ClickHouse and Plausible have different startup behavior. For Plausible v3.2.1, the `run` command calls `/app/bin/plausible start` which boots the Elixir release but does NOT apply database migrations. Without migrations, the app crashes with `relation "salts" does not exist`.

**REQUIRED for Plassible v3.2.1:**

```dockerfile
FROM ghcr.io/plausible/community-edition:v3.2.1

ENV PORT=8000

# Explicit migration command required — base image does NOT auto-migrate
CMD ["/bin/sh", "-c", "/entrypoint.sh db migrate && /entrypoint.sh run"]
```

This is the ENTIRE Dockerfile that works for Plausible on Railway.

### Debugging Entrypoints

When Railway shows `exec: line N: <something>: not found`:
1. Pull the base image: `podman pull <image>`
2. Read the entrypoint: `podman run --rm --entrypoint /bin/sh <image> -c "cat /entrypoint.sh"`
3. Identify what subcommands the entrypoint actually supports
4. Build your CMD around those exact subcommands

Common pattern: entrypoints use a `case` or `if/elif/else` chain. Anything that falls through to `exec "$@"` is treated as a shell command, NOT a subcommand.
