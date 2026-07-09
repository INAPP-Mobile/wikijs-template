# Pre-Flight Checklist (Deep-Dive)

**The 12-step gate you run BEFORE any new template scaffold, template-vars.json edit, or new deploy test.** Each step is a verification command + a "what to check" + a "common gotcha". The one-page summary lives at the top of `railway-deployment/SKILL.md`.

> **Why this exists:** the railway-ghost session (2026-07-09) and the plausible/blinko sessions before it all hit the same trial-and-error patterns: URL ordering crashes, raw-image sibling macro resolution, 2-boot deadlocks, plugin-var leakage, lost+found PGDATA traps, etc. Each of those is now a step below.

> **Structure:** Step 1 = project metadata rules (icon/name/draft/submodule), Step 2 = auth, Steps 3-9 = technical gates (TOML/image/macros/init-time/volume/two-file/plugin-var), Step 10 = project metadata (dedup — uniqueness), Steps 11-12 = lifecycle (clean-slate/test-deploy).

---

## Step 1 — AGENTS.md Project Rules

**What to do:** Confirm the template complies with the project's own rules (AGENTS.md rules 1-3 + 7) BEFORE doing any technical work.

```bash
# Rule 1: Icon is graphical-only (no text/tspan)
grep -nE '<text|<tspan' template-icon.svg 2>/dev/null && err "Icon has text elements" || ok

# Rule 2: Display name is sentence case (e.g., "Plausible CE", not "plausible-ce")
# Check the name in the project (if it already exists) or in your local naming plan
echo "$DISPLAY_NAME" | grep -qE '^[A-Z][a-zA-Z0-9]*([ -][A-Z][a-zA-Z0-9]*)*$' && ok || err

# Rule 3: Template is DRAFT, not PUBLISHED (NEVER auto-publish)
railway templates list --json | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', data.get('data', []))
for t in items:
    if t.get('code') == '<your-code>':
        print('PUBLISHED' if t.get('status') == 'PUBLISHED' else 'DRAFT')
        break
"

# Rule 7: If pushing a submodule, verify the remote before push
git ls-remote <remote-url>  # must resolve to the expected repo
cat .git/config | grep -A2 'remote "origin"'  # must point to the right URL
```

**What to check:**
- Icon has no `<text>` or `<tspan>` elements
- Display name is sentence case
- If the template already exists on Railway, it's in DRAFT (UNPUBLISHED) state
- If this template is a submodule, the remote URL is the correct one for THIS submodule (not a different template's remote)

**Common gotcha — icon vs. og-image confusion.** `template-icon.svg` is the small icon shown on the marketplace card (graphical only). `og-image.svg` is the social-share preview image (CAN have text — it's a banner). Don't confuse them. See AGENTS.md rule 1.

**Common gotcha — sentence case for native lowercase app names.** Some apps (e.g., `umami`, `kuma`) are legitimately lowercase. Use the upstream's canonical capitalization. AGENTS.md rule 2 says sentence case UNLESS the upstream name is itself lowercase.

**Common gotcha — submodule push clobber.** The parent monorepo's `remote.origin-wikijs.url` may be misconfigured (e.g., pointing to `wikijs-template.git` when you're actually pushing a different submodule). Always confirm with `git ls-remote <url>` + `cat .git/config` BEFORE `git push`. See AGENTS.md rule 7.

---

## Step 2 — Auth + Token Health

**What to do:** Confirm the Railway CLI is authenticated and the token is fresh.

```bash
unset RAILWAY_TOKEN  # CRITICAL — see common gotcha
railway whoami 2>&1 | grep -qE '@' && echo "OK" || echo "FAIL: run: railway login"
```

**What to check:** `railway whoami` returns a user/email line. If it returns "Unauthorized" → re-auth.

**Common gotcha — `RAILWAY_TOKEN` env var makes write commands fail.** When the `RAILWAY_TOKEN` env var is set in the shell, the CLI uses it INSTEAD of the token in `~/.railway/config.json` (set by `railway login`). Bearer tokens work fine for GraphQL queries via `curl -H "Authorization: Bearer $TOKEN"`, but **CLI write commands (`railway up`, `railway variables set`, `railway templates create`) silently fail** when `RAILWAY_TOKEN` is exported. Always `unset RAILWAY_TOKEN` before write commands. (The CLI uses the config.json token after `railway login`.)

**Auth expires frequently in long sessions.** If a deploy test takes >5 min, expect to need to re-auth. See `references/railway-template-publish-workflow.md` for the full CLI auth boundary.

---

## Step 3 — TOML Syntax

**What to do:** If `railway.toml` exists, verify it parses. Hand-editing commonly drops `=` signs.

```bash
# In the template dir:
[ -f railway.toml ] && python3 -c "import tomllib; tomllib.load(open('railway.toml','rb')); print('TOML OK')" || echo "no railway.toml (ok for single-service Dockerfile-only)"
# Find missing = signs:
grep -nE '^\w+ "[^"]*"$' railway.toml 2>/dev/null
```

**What to check:** "TOML OK" + no lines matching the missing-`=` regex. Every `key "value"` must be `key = "value"`.

**Common gotcha — silent rejection.** A single `key "value"` instead of `key = "value"` causes Railway to silently reject the file → no services defined → no build → no error about TOML. The ONLY symptom is "Deployment does not have an associated build" with no build logs. See `references/first-step-toml-syntax-diagnostics.md`.

---

## Step 4 — Upstream Image Inspection

**What to do:** BEFORE writing the Dockerfile, inspect the upstream image's entrypoint, default CMD, and app install directory. Don't guess.

```bash
IMAGE=ghost:6.51.0-alpine  # replace with your image
podman pull "$IMAGE"

# Read the entrypoint script
podman run --rm --entrypoint /bin/sh "$IMAGE" -c "cat /entrypoint.sh 2>/dev/null | head -50"
# OR for ENTRYPOINT-formatted:
podman run --rm --entrypoint /bin/sh "$IMAGE" -c "cat /entrypoint* 2>/dev/null | head -50"

# Find the app install dir
podman run --rm --entrypoint /bin/sh "$IMAGE" -c "ls -la / /var/lib/ /app/ /opt/ /usr/src/ 2>/dev/null"

# Default CMD + ENTRYPOINT
podman inspect "$IMAGE" --format '{{json .Config.Cmd}}'
podman inspect "$IMAGE" --format '{{json .Config.Entrypoint}}'

# What user does the process run as?
podman inspect "$IMAGE" --format '{{.Config.User}}'
```

**What to check:**
- Entry script subcommands (often `if [ "$1" = 'run' ]; ... elif [ "$1" = 'migrate' ]; ...`) — build your CMD around these
- Where the app actually lives (`/var/lib/<app>/current/`, `/app/`, `/opt/<app>/`, etc.) — your COPY targets depend on this
- What the default CMD is — your override must work with or replace this
- What user the process runs as (often `node`, `app`, `1000`) — your volume mounts need to be writable for that UID

**Common gotcha — overriding ENTRYPOINT incorrectly.** Some images use an entrypoint script that handles permissions + bootstrapping (e.g., Ghost's `docker-entrypoint.sh`). If you override `ENTRYPOINT` in your Dockerfile, you lose that. Either: (a) keep the upstream entrypoint + only override `CMD`, or (b) explicitly replicate the entrypoint's logic.

**Common gotcha — wrong COPY path.** If the upstream image has a `current/` version-symlink (Ghost does), the app dir is `/var/lib/<app>/current/`, NOT `/var/lib/<app>/`. `podman run --rm ... -c "ls -la /var/lib/"` reveals this. See `template-deploy-pitfalls.md` § 3 for the full warning.

---

## Step 5 — Macro Resolution Plan

**What to do:** Identify what `${{...}}` macros the template will need. Map each to a known-good pattern from the matrix.

| Need | Macro | Resolves? | Pattern |
|------|-------|:---:|---------|
| Public URL | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | ✅ after `railway domain` | See § 1 of `template-deploy-pitfalls.md` |
| Random secret | `${{secret(64)}}` | ✅ | Use for SECRET_KEY_BASE, JWT secrets, etc. |
| DB host (raw sibling) | `${{MySQL.RAILWAY_PRIVATE_DOMAIN}}` | ✅ CLI / unverified marketplace | Tier 2 of `template-deploy-pitfalls.md` § 2 |
| DB plugin var | `${{Postgres.DATABASE_URL}}` | ❌ empty | Use component vars (`POSTGRES_USER`, etc.) instead |
| DB plugin var (Postgres) | `${{Postgres.POSTGRES_*}}` | ❌ empty | Same — use component vars |

**What to check:** Every `${{...}}` in your `template-vars.json` is in the ✅ row of the matrix. Any in the ❌ row → restructure.

**Common gotcha — the matrix is incomplete for cross-service system vars.** `${{MyService.RAILWAY_PRIVATE_DOMAIN}}` (a system var referenced cross-service) is NOT explicitly in the matrix. It worked in a CLI `railway up` test but has NOT been verified in a marketplace form deploy. Always do an end-to-end marketplace test before publishing if you rely on this pattern. See `template-deploy-pitfalls.md` § 2 Tier 2 for the warning.

**Common gotcha — the 3 marketplace bugs that hit EVERY Postgres/ClickHouse template:**
1. `${{RAILWAY_PUBLIC_DOMAIN}}` resolves **without** the `https://` prefix → use `https://${{RAILWAY_PUBLIC_DOMAIN}}`
2. `${{Postgres.DATABASE_URL}}` resolves empty → use sibling service + hardcoded credentials OR set `POSTGRES_PASSWORD` in the form
3. `${{clickhouse.CLICKHOUSE_USER}}`/`PASSWORD` resolve empty → either set them in the form OR use a post-deploy fix

See `railway-template-variables` SKILL.md § "Marketplace Deploy Issues" for the full table.

---

## Step 6 — Init-Time Self-References (The 2-Boot Workaround)

**What to do:** Check if the upstream app's boot calls a local API that needs DB records to exist yet. Examples: some apps (e.g., Ghost 6) have a feature that, during first boot, tries to fetch a record from a local API endpoint that needs an "owner" user that doesn't exist yet.

**How to check:**
- Read the upstream app's boot/init code (GitHub source)
- Search for: `fetch(`, `localhost`, `127.0.0.1`, `webhookSecret`, `first boot`, `seed`
- If the app's README mentions "first run" or "initialization" — probably has this pattern

**What to do if yes:** Add a **preconfig script** that runs BEFORE the main app, disables the offending feature via SQL, and tolerates a **2-boot sequence**:

```dockerfile
# In the Dockerfile (paths generalized — adapt to your image's app dir):
COPY bin/preconfig.js /<app-dir>/bin/preconfig.js
HEALTHCHECK --start-period=120s ... CMD ...
CMD ["sh", "-c", "node /<app-dir>/bin/preconfig.js; exec <main-app-cmd>"]
```

**What to check:** The preconfig script:
- Always exits 0 (never crashes the deploy)
- Has a "table missing" branch that no-ops gracefully (so boot #1 still proceeds)
- Uses `;` not `&&` in the CMD (so the main app starts even if preconfig failed for any reason)
- Bump `HEALTHCHECK --start-period=120s` to cover the 2-boot window

**Common gotcha — `&&` vs `;` in CMD.** `&&` chains: if preconfig exits non-zero, the main app never starts. `;` chains: preconfig runs (or fails), then main app starts regardless. Use `;` for the preconfig → main-app chain. The final command (the main app) should still use `exec` so SIGTERM is forwarded to it. See `template-deploy-pitfalls.md` § 3 for the full implementation pattern.

**When to skip this:** If the deadlock is in critical-path code (no setting can disable it), or if upstream has a known fix in a newer version. Then either upgrade the upstream version or use a different template.

---

## Step 7 — Volume Mount Geometry

**What to do:** For raw-image siblings (not plugins), use the parent-mount geometry. For app-owned data, follow the upstream image's Dockerfile.

| Service | Volume mount path | Why |
|---------|-------------------|-----|
| Raw `postgres:16-alpine` sibling | `/var/lib/postgresql` (NOT `/var/lib/postgresql/data`) | Avoid the ext4 `lost+found/` PGDATA crash |
| Raw `mysql:8` sibling | `/var/lib/mysql` | Standard |
| App-owned data | Whatever the upstream image's Dockerfile uses | Don't guess — `podman inspect` to see the expected path |

**What to check:** The volume mount path in `railway.json` matches the upstream's expected path. If the upstream entrypoint enforces a path prefix (e.g., Postgres plugin enforces `PGDATA=/var/lib/postgresql/data`), the volume must be mounted at the PARENT path so the lost+found/ at the volume root is OUTSIDE the data dir.

**Common gotcha — postgres-ssl:18 plugin lost+found crash.** Railway volumes always have an ext4 `lost+found/` directory at the volume root. The `postgres-ssl:18` plugin forces the volume mount at `/var/lib/postgresql/data` (trapping lost+found/ inside PGDATA), causing `initdb: directory exists but is not empty`. Fix: use a sibling `postgres:16-alpine` service (not the plugin) + mount at the parent path `/var/lib/postgresql`. See `references/plausible-ce-and-postgres-docker-patterns.md` § "Lost+Found Gotcha".

**Common gotcha — don't set PGDATA manually.** The Postgres plugin auto-injects `PGDATA=/var/lib/postgresql/data`. Manually setting `PGDATA=/var/lib/postgresql/data/pgdata` (with a trailing subpath) crashes the plugin. Either let the plugin manage it OR use a sibling service.

---

## Step 8 — Two-File Sync

**What to do:** Both `template-vars.json` (source of truth) and `template-editor-raw.json` (deploy form) must exist with **identical keys in identical order**. Validate the JSON is parseable.

```bash
python3 -c "import json; print(len(json.load(open('template-vars.json'))), 'vars')"
python3 -c "import json; print(len(json.load(open('template-editor-raw.json'))), 'editor-raw vars')"
# Check key parity:
python3 -c "
import json
a = set(json.load(open('template-vars.json')).keys())
b = set(json.load(open('template-editor-raw.json')).keys())
print('only in vars:', a - b)
print('only in editor-raw:', b - a)
"
```

**What to check:** Both files parse, same number of keys, no key in one but not the other.

**Common gotcha — `defaultValue` vs `value` schema mismatch.** `template-vars.json` uses `{ "defaultValue": ..., "description": ..., "isOptional": ... }`. `template-editor-raw.json` uses `{ "value": ..., "description": ... }`. The pipeline auto-converts, but if you hand-edit one file, the schema can drift. See `railway-template-variables` SKILL.md § "Field Mapping Schema" for the full table.

**Common gotcha — per-service file layout for multi-service templates.** Each service in a multi-service template gets its own subdir with its own `template-vars.json` + `template-editor-raw.json`. Plugin services (Postgres, MySQL via plugin) get NO form files — Railway auto-injects.

```
<template>/
├── template-vars.json              # Main service source truth
├── template-editor-raw.json        # Main service deploy form
├── <companion-service>/
│   ├── template-vars.json
│   └── template-editor-raw.json
└── companion-mapping.json          # Maps plugin → companion vars
```

---

## Step 9 — No Plugin-Var Leakage

**What to do:** Verify `${{Postgres.DATABASE_URL}}`, `${{Postgres.POSTGRES_*}}`, `${{MySQL.MYSQLHOST}}` etc. do NOT appear in `template-vars.json` or `template-editor-raw.json`. The Railway plugin auto-injects these; declaring them in the form causes the "empty textboxes" bug or stale-credential crash.

```bash
# CRITICAL — these patterns should produce ZERO matches:
grep -nE '\${{\s*(Postgres|MySQL|Redis|MongoDB)\.\s*(DATABASE_URL|POSTGRES_|MYSQL|MARIADB)' template-vars.json template-editor-raw.json 2>/dev/null
grep -nE '\${{\s*clickhouse\.' template-vars.json template-editor-raw.json 2>/dev/null  # ClickHouse is the exception (no plugin)
```

**What to check:** No plugin-style macro references in the form files. ClickHouse IS the exception (no Railway plugin for it; you must declare `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DB` in the form).

**Common gotcha — empty textbox UX bug.** If you add `postgres/template-editor-raw.json` for a Postgres plugin service, the dashboard shows empty textboxes with asterisks (`PGDATA * Value [empty]`). The user has no idea what to fill. Fix: **delete the form files entirely** for plugin services. See `railway-template-variables` SKILL.md § "Companion Service Plugin Variables — CRITICAL RULE".

**Common gotcha — capturing manual overrides.** If the live project has a manually-set `DATABASE_URL`, `railway templates create` captures it into the template's form. Future deploys then have a hardcoded `DATABASE_URL` that goes stale. Fix: remove all manual overrides before `templates create` (see Step 11).

---

## Step 10 — Dedup Check (Template Name Uniqueness)

**What to do:** Before scaffolding a new template, confirm the template name/code doesn't already exist on Railway (in this workspace or in the marketplace).

```bash
# Set the new code in ONE place (used by both the bash check and the embedded python):
NEW_CODE="<your-code>"

# Check if the template code already exists in this workspace.
# (Use a heredoc to avoid bash escaping issues with `python3 -c`.)
EXISTING=$(NEW_CODE="$NEW_CODE" railway templates list --json | python3 << 'PYEOF'
import sys, json, os
data = json.load(sys.stdin)
items = data
if not isinstance(items, list):
    items = data.get('items') or data.get('data') or []
if isinstance(items, dict):
    items = list(items.values())
codes = [t.get('code', '') for t in items]
print('EXISTS' if os.environ.get('NEW_CODE', '') in codes else 'OK')
PYEOF
)
[ "$EXISTING" = "EXISTS" ] && { err "Template '$NEW_CODE' already exists on Railway"; exit 1; }
ok "Template code is unique in this workspace"
```

**What to check:** The template code is unique. If `EXISTS`, choose a different code (e.g., append `-v2`, `-ce`, or a suffix).

**Common gotcha — substring match in both directions.** Dedup is not just exact-match. The `plausible` template conflicts with `plausible-2` (one is a substring of the other). The pipeline's dedup logic checks substring match in BOTH directions. If scaffolding a new template, run a substring check:

```python
def conflicts(new_code, existing_codes):
    new = re.sub(r'[\s_\-]+', '-', new_code.lower().strip())
    for code in existing_codes:
        old = re.sub(r'[\s_\-]+', '-', code.lower().strip())
        if new in old or old in new:
            return code
    return None
```

**Common gotcha — version suffix normalization.** `open-webui-3` normalizes to `open-webui-3` (no change). `plausible-2` and `plausible-ce` both normalize to `plausible-2` and `plausible-ce` (different). Strip version suffixes only if they're the same numeric suffix.

---

## Step 11 — Clean Slate Before `railway templates create`

**What to do:** Before generating a template from a working project, ensure no manual var overrides are captured. All service vars should resolve cleanly to `${{...}}` macros or be left unset.

```bash
# For each service in the project, list non-system vars:
for svc in <svc1> <svc2> <svc3>; do
  echo "=== $svc ==="
  railway variables --service "$svc" --kv | grep -v ^RAILWAY_
done

# Expected: 0 non-RAILWAY_ vars, OR all vars are ${{...}} macros
```

**What to check:** No service has a manually-set literal value. If any service has one:
1. Delete it: `railway variables delete KEY --service <svc>`
2. Re-deploy clean: `railway deployment redeploy --service <svc> --yes`
3. Verify: `railway variables --service <svc> --kv` should not show the literal

**Common gotcha — `template create` wipes dashboard fixes.** Regenerating a template (`railway templates create --project <id>`) reads the project's **runtime state** and destroys all dashboard editor fixes (buckets, variable defaults, icons, rootDirectory). **Generate once, then only use the dashboard editor.** See `railway-template-variables` SKILL.md § "⚠️ `template create` Wipes All Dashboard Fixes".

---

## Step 12 — Test Deploy + Final Verification (Before Publishing)

**What to do:** Deploy the project with `railway up` (or `railway up --detach` for non-interactive), poll for HTTP 200 on the service's primary route, and verify all critical env vars resolved (not empty).

```bash
# Trigger deploy
railway up --detach 2>&1 | tail -5

# Poll for HTTP 200 (with timeout)
DOMAIN=$(railway domain 2>&1 | grep -oE '[a-z0-9-]+\.up\.railway\.app' | head -1)
for i in $(seq 1 24); do
  sleep 15
  HTTP=$(curl -sS -o /dev/null -w "%{http_code}" "https://$DOMAIN/" 2>/dev/null || echo "000")
  echo "[t+$((i*15))s] HTTP $HTTP"
  if [ "$HTTP" = "200" ]; then break; fi
done

# Get latest deploy ID (with retry — returns null for 30-60s after railway up).
# Inlined python heredoc (avoids bash escaping issues with `python3 -c`).
# $TOKEN comes from Step 0c (read from ~/.railway/config.json).
SVC_ID="<your-service-id>"
LATEST_DEPLOY_ID=""
for i in 1 2 3 4 5 6 7 8; do
  LATEST_DEPLOY_ID=$(SVC_ID="$SVC_ID" curl -sS -m 15 https://backboard.railway.com/graphql/v2 \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "import json,os; print(json.dumps({'query':'query(\$id:String!){service(id:\$id){latestDeploy{id}}}','variables':{'id':os.environ['SVC_ID']}}))")" \
    | python3 << 'PYEOF'
import sys, json
try:
    r = json.load(sys.stdin)
    d = ((r.get('data') or {}).get('service') or {}).get('latestDeploy') or {}
    print(d.get('id', ''))
except Exception:
    print('')
PYEOF
  )
  [ -n "$LATEST_DEPLOY_ID" ] && break
  echo "  latestDeploy not ready yet (attempt $i/8), sleeping 15s..."
  sleep 15
done
[ -z "$LATEST_DEPLOY_ID" ] && err "latestDeploy never became available after 2 min"

# Final var-resolution verification
for svc in <main_svc> <companion_svc>; do
  echo "=== $svc vars ==="
  railway variables --service "$svc" --kv | grep -E '(URL|HOST|PASSWORD|TOKEN|SECRET|DOMAIN)=' | grep -v ^RAILWAY_
done

# Expected: no empty values for URL/HOST/PASSWORD/etc.
```

**What to check:**
- Primary route returns HTTP 200 within the polling budget
- No `=` (empty) values in critical vars (DATABASE_URL, BASE_URL, *_PASSWORD, etc.)
- All services are `Online` in `railway status`

**Common gotcha — `railway up` doesn't resolve macros.** `railway up` deploys do NOT resolve `${{...}}` macros. They only work in template marketplace deploys. So your CLI test will have empty `DATABASE_URL` even if the template will work in the marketplace. Test BOTH paths:
1. CLI deploy (`railway up`): tests the Dockerfile + image + build
2. Marketplace deploy (via the template form on dashboard): tests the full template including macro resolution

**Common gotcha — auth silently expires.** During a long deploy (5+ min), the auth token may expire. The deploy silently fails (no error, just no effect). If you see `Application not found` (404) for many minutes, re-auth with `railway login` and retry.

**Common gotcha — `latestDeploy` returns null briefly.** After `railway up`, the GraphQL `service { latestDeploy { id } }` query returns `null` for 30-60s while Railway creates the deploy record. The example above shows the retry loop — up to 8 attempts × 15s = 2 min budget. If still null after 2 min, the deploy itself likely failed (check `railway status`).

---

## Pre-Publish Final Checklist (After Step 12 Passes)

- [ ] AGENTS.md rules 1-3 + 7 followed (icon = graphical, name = sentence case, DRAFT only, submodule remote verified)
- [ ] All services `Online` (`railway status`)
- [ ] Primary route returns HTTP 200 (curl test in Step 12)
- [ ] Critical vars resolved (no `=` empty values)
- [ ] No plugin-style macros in form files (Step 9)
- [ ] No `${{Postgres.DATABASE_URL}}` in template-vars.json (Step 9)
- [ ] Template code is unique (Step 10)
- [ ] `publish-record.json` updated with the new template code

**Then:** `railway templates create --project <id> --json` → user opens dashboard editor → user runs `railway templates publish <code> --category "..." --description "..." --readme-file README.md` (NEVER auto-publish — see AGENTS.md rule 3).

---

## Cross-References

- `template-deploy-pitfalls.md` — Generic 3-lesson pitfalls (URL ordering, raw-image sibling, 2-boot)
- `first-step-toml-syntax-diagnostics.md` — Deep-dive on Step 3
- `plausible-ce-and-postgres-docker-patterns.md` — Deep-dive on Step 7 (lost+found + PGDATA)
- `postgres-component-vars-vs-database-url.md` — Deep-dive on Step 9
- `railway-template-publish-workflow.md` — End-to-end publish flow (the canonical reference for Steps 11-12)
- `railway-template-variables` SKILL.md — Two-file sync, marketplace macro resolution matrix
- `railway-graphql-misleading-errors-and-verify-discipline.md` — Verify-after-mutate discipline (applies to Step 12)
- `AGENTS.md` — Rules 1-3 (icon/name/draft) + rule 7 (submodule remote) — covered in Step 1
