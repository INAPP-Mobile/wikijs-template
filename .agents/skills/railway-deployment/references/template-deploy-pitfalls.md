# Template Deploy Pitfalls (Generic)

**Distilled from the railway-ghost session (2026-07-09), now archived.** These three pitfalls apply to **any** template that hits them — not just Ghost. Read before designing any new template that uses a `url=` env var, a raw DB image sibling, or a service with init-time self-references.

---

## 1. URL Ordering Pitfall: `url=https://${{RAILWAY_PUBLIC_DOMAIN}}` Resolves Empty

**Symptom:** First deploy crashes during a database-migration step with:

```
TypeError [ERR_INVALID_URL]: Invalid URL
    at new URL (...)
    at <app>/migrations/2-create-fixtures.js
```

The `url` env var is set to `https://${{RAILWAY_PUBLIC_DOMAIN}}`, which at the time of the migration is **`https://`** (empty domain — no domain has been assigned yet).

**Why:** `RAILWAY_PUBLIC_DOMAIN` is a **system variable** that only gets populated after `railway domain` (or the dashboard equivalent) has generated a public domain for the service. The migration runs at build/boot time, before any HTTP request has been routed.

**Fix (one of):**

1. **Generate the domain BEFORE the first deploy** (CLI/test path — recommended):
   ```bash
   railway domain                    # creates the public domain
   # THEN: railway up / variables set / etc.
   ```
2. **Set the URL to a literal value** after generating the domain (CLI/test path):
   ```bash
   DOMAIN=$(railway domain | grep -oE '[a-z0-9-]+\.up\.railway\.app' | head -1)
   railway variables set --service <ID> "url=https://$DOMAIN"
   ```
3. **Marketplace deploys** — the form's URL input doesn't exist at deploy time, so the `url` env var must be either:
   - Optional (`isOptional: true`) so the form lets the user set it after deploy
   - Prefixed with `https://${{RAILWAY_PUBLIC_DOMAIN}}` AND the template must tolerate a failing first-deploy + auto-restart (fragile UX — prefer option 1 for tests, option 2 for production)

**The macro resolution matrix** (verified 2026-07-09, three deploy tests):
| Macro | Resolves? |
|-------|:---:|
| `${{RAILWAY_PUBLIC_DOMAIN}}` | ✅ Domain only (after `railway domain`) |
| `${{secret(N)}}` | ✅ Random value |
| `${{MyService.RAILWAY_PRIVATE_DOMAIN}}` | ✅ (private intra-cluster DNS) |
| `${{MyService.PLUGIN_VAR}}` (e.g. `${{MySQL.MYSQLHOST}}`) | ❌ Empty for raw-image siblings |

---

## 2. Raw-Image Sibling: Plugin-Style Macros Resolve Empty

**Symptom:** App fails to connect to its database with errors like `connect ECONNREFUSED` or `getaddrinfo ENOTFOUND` — even though the sibling service is running and the env vars are set.

**Why:** When a sibling service is created from a **raw image** (e.g. `railway add --image mysql:8`) instead of the Railway **plugin** (e.g. `ghcr.io/railwayapp-templates/postgres-ssl:18`), the Railway-style plugin macros like `${{MySQL.MYSQLHOST}}` do **not** resolve. The plugin's auto-injected vars (which set `MYSQLHOST`, `MYSQLUSER`, etc. as Railway service references) are absent on raw images.

**Fix (3-tier decision tree — pick the most reliable for your case):**

**Tier 1 — Use the Railway plugin image (most reliable for marketplace):**
```bash
# In template, no special env var wiring needed; consumer refs work:
railway add --image ghcr.io/railwayapp-templates/mysql-ssl:8 -s MySQL
# Consumer: database__connection__host=${{MySQL.MYSQLHOST}}  # resolves correctly
```
✅ Plugin-injected vars (`MYSQLHOST`, `MYSQLUSER`, etc.) resolve in both CLI and marketplace deploys.
⚠️ Plugin images add opaque behavior (volume-mount geometry, init order) — test the full flow.

**Tier 2 — Raw image + component-var pattern (CLI-verified, marketplace-unverified):**
```bash
# CORRECT (CLI-tested in 2026-07-09 Ghost session; marketplace NOT verified):
railway variables set --service <APP_ID> \
  'database__client=mysql' \
  'database__connection__host=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}' \
  'database__connection__user=root' \
  'database__connection__password=${{MySQL.MYSQL_ROOT_PASSWORD}}' \
  'database__connection__database=${{MySQL.MYSQL_DATABASE}}' \
  'database__connection__port=3306'
```
⚠️ `RAILWAY_PRIVATE_DOMAIN` is a **system variable** that should resolve cross-service. The pattern WORKED in a CLI `railway up` test but has NOT been verified in a marketplace form deploy. **Before publishing**, test the template's marketplace form once end-to-end and confirm the connection works.
⚠️ The skill's macro resolution matrix flags ALL cross-service refs as "resolve empty" — the matrix doesn't have an explicit row for `MyService.RAILWAY_PRIVATE_DOMAIN`, so the marketplace behavior is unverified by the matrix, not contradicted by it.

**Tier 3 — Raw image + hardcoded internal DNS (works everywhere but very brittle):**
```bash
# Relies on Railway's stable intra-cluster DNS convention:
railway variables set --service <APP_ID> \
  'database__connection__host=mysql.railway.internal' \
  'database__connection__user=root' \
  'database__connection__password=${{MySQL.MYSQL_ROOT_PASSWORD}}' \
  'database__connection__database=${{MySQL.MYSQL_DATABASE}}' \
  'database__connection__port=3306'
```
✅ No macro resolution risk — works in both CLI and marketplace.
⚠️ **Very brittle.** Railway's internal DNS matches the service name **case-sensitively and exactly** — `mysql.railway.internal` only resolves if the sibling is literally named `mysql` (lowercase). Even `Mysql` or `MySQL` breaks it. **If you use Tier 3, the template MUST also hardcode the sibling creation with the matching lowercase name:** `railway add --image mysql:8 -s mysql` (NOT `-s MySQL`). If you can't enforce the sibling name, use Tier 1 or Tier 2.

**WRONG — never use plugin-style macros with a raw-image sibling:**
```bash
railway variables set --service <APP_ID> \
  'database__connection__host=${{MySQL.MYSQLHOST}}' \    # ❌ resolves empty
  'database__connection__user=${{MySQL.MYSQLUSER}}' \    # ❌ resolves empty
  'database__connection__password=${{MySQL.MYSQLPASSWORD}}'  # ❌ resolves empty
```
`MYSQLHOST`/`MYSQLUSER`/`MYSQLPASSWORD` are **plugin-injected variables** (only set on plugin-image siblings, never on raw images).

---

## 3. Init-Time Self-Reference Deadlock (The 2-Boot Workaround)

**Symptom:** Service is "Online" (process is running) but every HTTP route returns 502. Deploy logs show no fatal error, just a stuck init step like:

```
[activity-pub] No webhook secret found - cannot initialise
[activity-pub] retrying in 5s...
[activity-pub] No webhook secret found - cannot initialise
```

**Why:** Some apps have a service that, during its own boot, tries to call a **local HTTP API endpoint** that requires a database record (e.g. an "owner" user) which doesn't exist yet on a fresh install. The API returns 404/401, the service can't initialize, but the failure is "graceful" (logged, retried) — the process never exits, the healthcheck never sees a fatal error, and the HTTP server is in a 502-loop because it depends on the unfinished init.

**Fix:** Add a **preconfig script** that disables the offending service at the **DB level** (via a direct `UPDATE settings` SQL statement), run it BEFORE the main app, and accept the **2-boot sequence**:

1. **Boot #1:** Preconfig runs, the relevant DB table doesn't exist yet (migrations haven't run), the SQL is a no-op. Main app boots, hits the deadlock, healthcheck fails, Railway restarts.
2. **Boot #2:** Migrations have run (tables exist), preconfig's SQL succeeds, the offending service is disabled, main app boots cleanly, HTTP 200.

**Implementation pattern** (Dockerfile + a `bin/preconfig.js` script, paths generalized — adapt to your image's app directory):

```dockerfile
# Copy the preconfig script into the upstream image's app directory.
# (For Node images, this is typically `/var/lib/<app>/current/bin/` or
# `/app/bin/` depending on the image — inspect with
# `podman run --rm --entrypoint /bin/sh <image> -c "ls -la /var/lib/"`.)
COPY bin/preconfig.js /<app-dir>/bin/preconfig.js

# Bump start-period to cover the 2-boot window
HEALTHCHECK --start-period=120s ... CMD ...

# Run preconfig before the main app. `;` (not `&&`) so the app starts
# even if preconfig exits non-zero for any reason.
CMD ["sh", "-c", "node /<app-dir>/bin/preconfig.js; exec <main-app-cmd>"]
```

**⚠️ The "app directory" is image-specific and easy to get wrong.** Don't guess — inspect the upstream image first:

```bash
# Find where the app actually lives:
podman run --rm --entrypoint /bin/sh <image:tag> -c "ls -la /"
podman run --rm --entrypoint /bin/sh <image:tag> -c "ls -la /var/lib/ 2>/dev/null; ls -la /app/ 2>/dev/null; ls -la /opt/ 2>/dev/null"
# Find the upstream CMD (so you know what <main-app-cmd> is):
podman inspect <image:tag> --format '{{json .Config.Cmd}}'
```

Common patterns: `/var/lib/<app>/current/` (Ghost, with a `current/` version-symlink), `/app/` (Express.js slim images), `/opt/<app>/` (some Go/Java images), `/usr/src/app/` (generic Node). Get this wrong and the COPY silently places the script in a directory the runtime never looks at.

**Key preconfig-script requirements (generic, language-agnostic):**
- Use whatever driver is bundled with the upstream image (e.g., `mysql2/promise` for Node, `psycopg2-binary` for Python) — usually no new deps needed
- Connection-retry loop (e.g., 30 × 2s = 60s) to survive the DB still starting
- "Table missing" branch that **exits 0** (so the script doesn't crash the boot — boot #1 should still proceed to the deadlock + restart)
- "Table exists" branch that runs the `UPDATE` and **exits 0**
- Always exit 0 (never crash the deploy) — use `;` (not `&&`) in the CMD so the main app starts even if preconfig failed for any reason

**Mitigations:**
- Bump `HEALTHCHECK --start-period=120s` (or higher) to cover the full 2-boot window (~60-90s for the migration to run + the second boot to come up clean)
- **Document the 2-boot behavior** in the README troubleshooting table — first deploy 502 → Railway auto-restart → second deploy 200 is **expected**, not a bug
- Set `restartPolicyMaxRetries=10` in `railway.json` so a stuck init doesn't fail the deploy

**When to use this pattern:**
- App's init hits a local-API self-reference that needs a DB record to exist
- The offending feature is **optional** (disabling it via a setting is acceptable)
- The 2-boot UX is acceptable for the template's target audience

**When NOT to use this pattern:**
- The deadlock is in critical-path code (no setting can disable it)
- The 2-boot UX is too surprising for the target audience
- Upstream has a known fix in a newer version (upgrade instead)

---

## Related Files

- `railway-graphql-misleading-errors-and-verify-discipline.md` — verify-after-mutate discipline (relevant when testing the URL fix via `templatePublish`)
- `postgres-component-vars-vs-database-url.md` — when to use component vars vs `${{Postgres.DATABASE_URL}}` (similar pattern, different DB)
- `stale-credentials-plugin-rotation.md` — duplicate same-type services cause `${{...}}` to silently resolve empty (related to pitfall #2)
- `base-url-required-checklist.md` — apps that need a non-empty public-URL var at boot
