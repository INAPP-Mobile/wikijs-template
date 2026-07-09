---
name: railway-template-variables
description: "Schema rules Railway template-vars.json template-editor-raw.json files. Pre-publish validation checks, field mappings, common pitfalls, plugin-managed var rules, two-file sync requirements, PGDATA volume path coordination, credential rotation gotchas, companion service linkage via companion-mapping.json and railway.toml plugins, deployment service structure (Dockerfile + dockerfile_path). Tags: [railway, template, deploy-form, variables, pitfalls, plugins, validation, PGDATA, credentials, companion-services]"
tags: [railway, template, deploy-form, variables, pitfalls, plugins, validation, PGDATA, credentials, companion-services]
---

# Railway Template: Variables, Services & Two-File Pattern

Railway template definitions use two JSON files with different schemas that must stay in sync. The pipeline auto-generates one from the other.

## File Roles

| File | Purpose | Schema |
|------|---------|--------|
| `template-vars.json` | Source truth — pipeline reads `defaultValue`, `description`, `isOptional` |
| `template-editor-raw.json` | Deploy form JSON for Railway Dashboard template editor — `value`, `description` |

## Companion Mapping Pattern

**When a template deploys multiple services where one references another's env vars, use three coordinated files:**

| File | Role | Sync rule |
|------|------|-----------|
| `companion-mapping.json` | Maps which plugin/service companion vars feed into the deploy form | Each clickhouse/postgres reference must clickhouse/ match an entry in the companion-mapping clickhouse/ block |
| `template-vars.json` | Deploy form source truth | Same number of keys as template-editor-raw.json |
| `template-editor-raw.json` | Deploy form editor JSON | Same number of keys, same order, same descriptions |

`template-vars.json` values reference the **exact case-sensitive service IDs** and **exact variable names** as provisioned on the linked services (e.g., `${{clickhouse.CLICKHOUSE_USER}}`, `${{clickhouse.CLICKHOUSE_PASSWORD}}`). Copy these directly by:

```bash
railway variables --service <id> --kv   # or --service clickhouse --kv
```


## Two-File Sync Requirement

Every variable in `template-vars.json` must appear in `template-editor-raw.json` in the same order. Pipeline regenerates the second one. Both must stay JSON-valid at lint time. See JSON validation checks step 8 pre-publish.

## Reference Documentation

- **Credential rotation, plugin var rules, PGDATA pitfalls, case-prefix rules, per-service var capture workflow:** [`references/credential-rotation.md`](references/credential-rotation.md)
- **Editor variable format, per-service file splitting, template lifecycle CLI, rename workflow:** [`references/template-editor-format.md`](references/template-editor-format.md)

## Directory Naming Convention

**New templates live monorepo root directly.** When user asks build template app`foo`:- Directory:`foo`(NOT`railway-foo`NOT`railway_foo`)
- Railway marketplace slug: derived directory name, not hardcoded- Git repo slug: app name only (Railway adds`template-`prefix URLs)**Rationale:** Avoids prefix pollution, deduplication clarity, natural project identity.Example:
```bash
python scripts/pipeline.py foo          # creates ./foo/
python scripts/pipeline.py railway-foo  # Also strips "railway-" prefix from argument
```## Companion Service Plugin Variables — CRITICAL RULE

**Companion service variables live INSIDE the service (auto-injected by Railway plugin). Do NOT re-export them in `template-vars.json` or `template-editor-raw.json`.**DANGER variables (`[[services.plugins]] name = "postgresql"`):- `DATABASE_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`- `PGDATA`If above appear inside deploy-form JSON cause:
1. **Empty deploy value `${{Postgres.DATABASE_URL}}` resolves `""`** when wrong number, typo, plugin miss, override plugin DATABASE_URL crash
2. **Stale creds when Railway rotates passwords** template hardcodes plugin rotates, auth fail crash loop
3. **PGDATA path mismatch crash** when user data dir not match Railway volume mount, refusing start PostgreSQL

When create template, manually remove all `POSTGRES_*`, `DATABASE_URL` `template-vars.json`/`template-editor-raw.json`, let Railway plugin inject. Use own override.**Exception:** ClickHouse does not plugin — keep `CLICKHOUSE_*` vars inside `template-editor-raw.json`.

See raw JSON data live project reference: [`references/service-raw-json-data.md`](references/service-raw-json-data.md)

## Field Mapping Schema

### template-vars.json (source truth for pipeline)
```json
{
  "VAR_NAME": {
    "defaultValue": "",
    "description": "Human readable description",
    "isOptional": true|false
  }
}
```

### template-editor-raw.json (GraphQL serializedConfig output)
```json
{
  "VAR_NAME": {
    "defaultValue": "",
    "isOptional": true|false
  }
}
```

### Editor variable format (Raw JSON editor — what actually validates)

The template editor's Raw JSON view **rejects** `defaultValue` / `isOptional`. It requires `{ "value": string, "description": string }`:

```json
{
  "BASE_URL": {
    "value": "${{RAILWAY_PUBLIC_DOMAIN}}",
    "description": "Public URL for Plausible"
  },
  "SECRET_KEY_BASE": {
    "value": "${{secret(64)}}",
    "description": "Cookie signing secret (64-char random)"
  },
  "DISABLE_REGISTRATION": {
    "value": "false",
    "description": "Set to true to disable public registration"
  }
}
```

**Why:** `templateGenerate` GraphQL mutation returns `defaultValue` + `isOptional`, but the editor's internal schema only accepts `value` + `description`. Pasting GraphQL output directly into the Raw JSON editor fails: `"JSON values must be strings or { value: string, description?: string | null }"`.

**Recovery workflow:**
1. `templateGenerate` → get service IDs + variable names from `serializedConfig`
2. Convert each var to `{ "value": ..., "description": ... }` format
3. Paste into matching service's `variables` key in Raw JSON editor

**Pitfall — `templateGenerate` strips literal values:** Railway expressions (`${{...}}`) survive as `defaultValue`, but plain literals (`false`, `plausible`, URLs) get stripped. Always restore literals using the editor format after generation.

### Per-service JSON file splitting (large payloads)

When the full `serializedConfig` is too large for the user to copy-paste from terminal output, split into per-service files containing **only the `variables` object** for each service:

```
railway-plausible/
├── plausible-ce.json      # just the variables object for plausible-ce
├── clickhouse.json        # just the variables object for clickhouse
└── plausible-postgres.json # just {} (plugin-managed, no vars)
```

Each file's content goes into the matching service's `variables` key in Raw JSON editor.

### Template rename workflow

GraphQL has **no `templateUpdate` mutation** — template names cannot be renamed via API. The template name is locked to the project name at `templateGenerate` / `templates create` time.

**To rename a template:**
```bash
# 1. Rename the project
# GraphQL: projectUpdate(id: "...", input: { name: "New Name" })

# 2. Delete the old draft
railway templates delete <old-template-id> --yes

# 3. Regenerate from renamed project
railway templates create --project <project-id> --json
```

**CLI命令参考（非交互）:**
```bash
railway templates list --json                    # 列出工作区模板
railway templates create --project <id> --json    # 从项目生成草稿
railway templates delete <id> --yes               # 删除草稿
railway templates publish <code> --category "..." --description "..." --readme-file README.md  # 发布
```

### Two-file sync (pipeline automation)

`template-vars.json`:
```json
{
  "VAR_NAME": {
    "defaultValue": "",
    "description": "Human readable description",
    "isOptional": true|false
  }
}
```

`template-editor-raw.json`:
```json
{
  "VAR_NAME": {
    "value": "",           // mirror defaultValue
    "description": "Human readable description"
  }
}
```

Notes:
- `value` mirrors `defaultValue` exactly
- `${{...}}` runtime macros work in both files (post-deploy interpolation)
- `optional` only used pipeline deploy form validation; does not generated JS pipeline
    "defaultValue": "",
    "description": "Human readable description",
    "isOptional": true|false
  }
}
````template-editor-raw.json`:
```json{
  "VAR_NAME": {
    "value": "",           // mirror defaultValue
    "description": "Human readable description"
  }
}
```Notes:
- ``value`` mirrors ``defaultValue`` exactly
- `${{...}}` runtime macros work both files (post-deploy interpolation)- `optional` only used pipeline deploy form validation; does not generated JS pipeline

## Runtime Macros

Supported form `${{reference}}`:
- `${{Postgres.DATABASE_URL}}` — Postgres connection string (Postgres plugin)
- `${{Postgres.POSTGRES_USER}}` — Postgres username (Postgres plugin)- `${{Postgres.POSTGRES_PASSWORD}}` — Postgres password (Postgres plugin)
- `${{Postgres.POSTGRES_DB}}` — Postgres database name (Postgres plugin)
- `${{Postgres.PGDATA}}` — Postgres data dir (Postgres plugin)- `${{Postgres.RAILWAY_PRIVATE_DOMAIN}}` — Postgres private DNS (Postgres plugin)
- `${{clickhouse.CLICKHOUSE_*}}` — ClickHouse companion service vars (no plugin, must be declared)- `${{RAILWAY_PUBLIC_DOMAIN}}` — project public URL- `${{secret(N)}}` — auto-generate N random bytes base64-encodedVault secrets: use `${{secret(64)}}` minimum `SECRET_KEY_BASE` 64 bytes required.

## Known Combinations That Break### Postgres plugin + DATABASE_URL in template-vars
See above.

### PGDATAVolume Mount ConflictWhen plugin injects `PGDATA=/var/lib/postgresql/data` Railway expects value start `/var/lib/postgresql/data`. Overriding string not matching volume path **refuses start**. **Rule:** not set `PGDATA` template; let plugin manage.### BASE_URL required, no default`BASE_URL` empty crashes Plausible: `** (RuntimeError) BASE_URL configuration option required.` **Rule:** Set default `${{RAILWAY_PUBLIC_DOMAIN}}` macro resolves correctly runtime.

### PGDATAMissingthen PostgreSQL never start, `DATABASE_URL` not injected (plugin crash causes plausible crash loop).

### Two Postgres Services single deployWhen two Postgres services exist inside one deploy, `${{Postgres.DATABASE_URL}}` macro resolves wrong empty. Delete duplicates before deploy.

### deploy comma-number pool size`DATABASE_POOL_SIZE` forces integer, not string. Enable string convert inside app.## JSON Validation

Both files must pass `python3 -json` validation missing trailing commas invisible Railway parser break deploy form.

```bash
python3 -c "import json; json.load(open('template-vars.json'));"python3 -c "import json; json.load(open('template-editor-raw.json'));"
```## Pipeline Generation Notes

Pipeline generate `template-vars.json` reading `Dockerfile` other artifacts. Does **not** generate plugin-managed vars.Pipeline cannot auto-detect `${{Postgres.DATABASE_URL}}` not injected plugin. Human must remove manually after pipeline step 7 generation.## Per-Service Directory Layout (Multi-Service Templates)

```
<template>/
├── template-vars.json              # Main service source truth
├── template-editor-raw.json        # Main service deploy form
├── <companion-service>/
│   ├── template-vars.json          # Companion service source truth
│   └── template-editor-raw.json    # Companion service deploy form
└── companion-mapping.json          # Maps plugin → companion vars
```

**Service naming:** NAME service directory = service name railway.toml `[[services]] name "..."` (case-sensitive).

Per-service template-editor-raw.json separate deploy form user sees click service tile.

## New Pitfalls 2026-07 (from session)

### Validate railway.toml Syntax Before Deploy (first diagnostic)

**Symptom:** `railway up` succeeds but `railway status` shows "Failed" and `railway logs` says "Deployment does not have an associated build". No build logs.

**Root cause:** `railway.toml` has invalid TOML syntax — most commonly `key "value"` instead of `key = "value"`. Railway silently rejects the file → no services → no build.

**First diagnostic step (ALWAYS):**
```bash
python3 -c "import tomllib; tomllib.load(open('railway.toml','rb')); print('TOML OK')"
grep -nE '^\w+ "[^"]*"$' railway.toml  # finds missing = signs
```

**Fix:** Add `=` signs. See `railway-deployment` skill → `references/first-step-toml-syntax-diagnostics.md`.

### Clean Slate Before `railway templates create`
`railway templates create` reads CURRENT project vars → writes `template-editor-raw.json`. Manual overrides get captured:

**Example bug:** User manually fixed `DATABASE_URL` in live project. New draft captured hardcoded `DATABASE_URL` → form showed extra var → deploy crashed.

**Rule:** Before `railway templates create`, remove all manual overrides ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### Postgres plugin form = just remove JSON files, NOT add labels
Add `postgres` block companion-mapping.json so plugin vars available as `${{Postgres.*}}` references template.

### TOML lint writes corrupt file
`write_file`/`patch` railway.toml triggered TOML lint — escapes escape sequences (`name "plausible"` → broken quotes). **Use heredoc** avoid:
```bash
cat > railway.toml << 'EOF'
[project]
name = "plausible"
...
EOF
```

### Unpublish requires interactive TTY yes pipe
```bash
yes | railway templates unpublish plausible-1 --yes
```

### companion-dockerfile-copy-gotcha

When a companion service has `source.rootDirectory` set (e.g., `"clickhouse"`), the build context IS that directory. The Dockerfile's COPY paths must be **relative**, not include the prefix:

```dockerfile
# WRONG (double-nested):
COPY clickhouse/logs.xml /etc/clickhouse-server/config.d/logs.xml

# RIGHT (relative to clickhouse/):
COPY logs.xml /etc/clickhouse-server/config.d/logs.xml
```

**Symptom:** `failed to compute cache key: ... "/clickhouse/file.xml": not found`

### CLI deploy creates duplicate services with no volumes

`railway deploy -t <code>` does NOT reuse existing services. It creates NEW services with randomized suffixes and does NOT:
- Resolve `${{...}}` template var syntax
- Create volume mounts
- Set any env vars

**Use case:** Only validates Dockerfile source builds correctly. NOT for template variable testing.

### terminals-cmd-chain

**ALWAYS `repr()` verify Dockerfile CMD chaining** — `cat` collapses `&&`.

## Companion vs Plugin Services — CRITICAL DISTINCTION

**Only services Dockerfile get deploy form JSON files. Plugins do not.**

| Type | Has own Dockerfile? | Has form JSON? | Auto-injects vars? |
|------|---------------------|----------------|---------------------|
| **Main** (plausible-ce) | Yes | Yes (template-editor-raw.json) | No |
| **Companion** (ClickHouse) | Yes | Yes (clickhouse/template-editor-raw.json) | No |
| **Plugin** (Postgres, MySQL, Redis) | No | NO — Railway auto-injects | Yes |

**Why:** Plugins attached railway.toml `[[services.plugins]]` Railway handles internally. Adding JSON files for them creates empty textboxes break auto-injection.

## Hardcoded Credentials Pitfall: Extracting Template From Live Project

When generating template files from working project, NEVER copy instance-specific secrets/defaults:

```json
// WRONG (captured live project):
"CLICKHOUSE_PASSWORD": "clickhouse_plausible_pw_2026",
"SECRET_KEY_BASE": "1r0csvaep4clkta54dbtel6n56kij...",
"BASE_URL": "https://plausible-production.up.railway.app"

// CORRECT (placeholder, Railway auto-generates):
"CLICKHOUSE_PASSWORD": "${{secret(24)}}",
"SECRET_KEY_BASE": "${{secret(64)}}",
"BASE_URL": "${{RAILWAY_PUBLIC_DOMAIN}}"
```

**Why:** Hardcoded secrets go stale across projects/domains. Auto-generate settings fresh each deploy.

To get correct placeholder values:
```bash
railway variables --service <svc> --kv   # note current values
# Then JSON files use placeholders above, NOT the live values
```

## Testing Workflow: Draft → Publish → Test → Finalize

```bash
# 1. Create template draft
railway templates create --project <id> --json

# 2. User ALWAYS confirms before publish (permission required)
railway templates publish <code> --category "Analytics" --description "..." --readme-file README.md

# 3. Test deploy unpublish before anyone else uses
railway templates unpublish <code> --yes

# 4. Fix republish iterate stable

# 5. Final publish (user confirms again)
railway templates publish <code> --category "Analytics" --description "..." --readme-file README.md
```

**CRITICAL: Always get explicit user permission before `railway templates publish`.** User retains control publication state.

**Draft templates cannot tested** `railway deploy --template <code>` fail templates unpublished. User must test via browser login.

## Reference

- Live service JSON dump reference: [`references/service-raw-json-data.md`](references/service-raw-json-data.md)
- Volumes + plugins config: see `railway-deployment` skill healthcheck + plugin patterns.

## New Pitfalls 2026-07-08 (Template Form — Definitive Variable Default Workflow)

### ⚠️ `template create` Wipes All Dashboard Fixes — Never Regenerate

**CRITICAL:** Regenerating a template from a project (`railway templates create --project <id>`) reads the project's **runtime state**, NOT the template editor's state. All dashboard fixes (buckets, variable defaults, icons, rootDirectory) are LOST.

**The correct workflow is ONE-TIME:**
1. Generate template once from the project
2. Apply ALL fixes in the dashboard editor
3. **Never regenerate from the project again** — only use `railway templates publish` to update

**Symptom of regeneration:** Template goes from 2 issues → 20 issues. All variable defaults become NONE. rootDirectory resets. volumeMounts vanish.

### Service Icons: `simpleicons.org` Serves HTML, Not SVG

**The URL `https://simpleicons.org/icons/plausibleanalytics.svg` does NOT serve a raw SVG** — it returns an HTML page. Browsers render this as a broken/default placeholder (e.g., SourceForge icon).

**Correct Simple Icons URLs** — use the raw GitHub CDN:
```
# WRONG (HTML page, not SVG):
https://simpleicons.org/icons/plausibleanalytics.svg

# RIGHT (raw SVG):
https://raw.githubusercontent.com/simple-icons/simple-icons/master/icons/plausibleanalytics.svg
```

**Railway DevIcons CDN** — use for Railway-curated icons (confirmed working):
```
https://devicons.railway.app/i/clickhouse.svg
https://devicons.railway.app/i/postgresql.svg
```
Note: `devicons.railway.app/i/plausible.svg` exists but is an API lookup service, not a stable static URL.

**Custom template-icon.svg** — committed to the repo, referenced via raw GitHub:
```
https://raw.githubusercontent.com/INAPP-Mobile/railway-plausible/main/template-icon.svg
```

### Template Icon vs Service Icon — They're Different

| Icon Type | Where Set | Where Visible |
|-----------|----------|---------------|
| **Template icon** | Dashboard template settings (upload) | Deploy page card, marketplace listing |
| **Service icon** | Per-service tile in template editor | Service tiles in projects deployed from template |

Service icons are stored in `serializedConfig.services.<id>.icon`. Template icon is NOT in serializedConfig — it's a separate template-level property set in the dashboard UI.

### `templateUpdate` Mutation Doesn't Exist — Dashboard Editor Only

**There is NO `templateUpdate` GraphQL mutation.** Template variables, icons, and config can ONLY be edited through the Railway dashboard template editor. The API is **read-only** for templates after creation (except for `templatePublish`, `templateUnpublish`, `templateDelete`).

**Attempting `templateUpdate` produces:** `HTTP Error 400: Bad Request` (unknown field/mutation).

### Buckets (Groups) — Root-Level Raw JSON Only

**Buckets define service groups** on the deploy page. They go in the **root-level Raw JSON** (alongside `services`), NOT in per-service Raw JSON:

```json
{
  "services": { ... },
  "buckets": {
    "databases": {
      "name": "Databases",
      "services": [
        "<postgres-service-id>",
        "<clickhouse-service-id>"
      ]
    }
  }
}
```

**Critical:** The service IDs in `buckets` MUST be the exact UUIDs from `serializedConfig`. Get them via:
```python
config = json.loads(template["serializedConfig"])
for sid, sdata in config.get("services", {}).items():
    print(f"{sdata['name']}: {sid}")
```

**Symptom of missing buckets:** Services appear ungrouped on the deploy page. Service layout (Shift+Click+drag in dashboard) is cosmetic only — it doesn't affect the template definition.

### Group Moving in Dashboard: Shift + Click + Drag

To move a service between groups in the dashboard template editor: **Shift + Click + mouse drag** (not regular drag). Regular drag expands the group instead of moving the service out.

### Dashboard Raw JSON Is the ONLY Path to Variable Defaults

**Confirmed: Neither CLI nor GraphQL can set template variable defaults.**

Both `railway templates create` and `templateGenerate` produce templates where all user-defined variables have `defaultValue: NONE` (or stripped to `isOptional: false` with no value). This is a platform limitation — not a bug.

**The confirmed one-click deploy workflow:**
1. Create template scaffold via CLI or GraphQL
2. Open dashboard editor → select service → Raw JSON
3. Paste the per-service variables JSON with `{ "value": "...", "description": "..." }` format
4. After pasting for all services, the deploy form shows all defaults filled

**Per-service JSON format (what the Raw JSON editor accepts):**
```json
{
  "VAR_NAME": {
    "value": "${{secret(24)}}",
    "description": "Human-readable description"
  }
}
```

**The editor REJECTS `defaultValue`/`isOptional` format** (which is what `templateGenerate` returns). Only `value`/`description` is accepted.

### Per-Service Directory Layout — CURRENT (sibling-service pattern, 2026-07-08)

```
<template>/
├── template-vars.json              # Pipeline source (defaultValue, isOptional)
├── template-editor-raw.json        # Generated from template-vars.json
├── plausible-ce.json               # → Paste into Plausible CE Raw JSON
├── clickhouse/
│   ├── Dockerfile
│   ├── railway.json
│   ├── template-vars.json          # Companion pipeline source
│   └── template-editor-raw.json    # → Paste into ClickHouse Raw JSON
└── postgres/                       # Sibling Postgres service (NEW 2026-07-08)
    ├── Dockerfile                  # FROM postgres:16-alpine (upstream, NOT postgres-ssl:18)
    ├── railway.json                # Minimal — no healthcheckPath
    ├── template-vars.json          # POSTGRES_USER/PASSWORD/DB + PGDATA defaults
    ├── template-editor-raw.json    # → Paste into Postgres tile Raw JSON
    └── .env.example                # Documents parent-mount geometry rationale
```

**Why sibling service instead of postgres-ssl:18 plugin:** Railway volumes always have ext4 `lost+found/` at the volume root. The postgres-ssl:18 plugin forces the volume mount at `/var/lib/postgresql/data`, trapping lost+found/ inside PGDATA — initdb then crashes with `directory exists but is not empty`. The sibling postgres:16-alpine service uses the upstream entrypoint (no PGDATA path-prepend enforcement) and mounts at the parent path `/var/lib/postgresql`, so lost+found/ lives outside PGDATA. See `references/plausible-ce-and-postgres-docker-patterns.md` § "Lost+Found Gotcha".

### templateGenerate: What Survives vs What Gets Stripped

`templateGenerate` reads project runtime variables. Behavior:

| Value Type | Example | Template Result |
|-----------|---------|----------------|
| `${{...}}` macro | `${{RAILWAY_PUBLIC_DOMAIN}}` | Survives as `defaultValue` |
| `${{secret(N)}}` macro | `${{secret(64)}}` | Survives as `defaultValue` |
| `${{Postgres.DATABASE_URL}}` | Plugin reference | Survives as `defaultValue` |
| Literal string | `plausible` | **Stripped to NONE** |
| Literal boolean | `false` | **Stripped to NONE** |
| Literal URL | `http://clickhouse:8123/plausible` | **Stripped to NONE** |

**Implication:** Even after `templateGenerate`, you MUST paste literal values (`false`, `plausible`, connection URLs) into the dashboard editor. Only `${{...}}` expressions survive generation.

### variableUpsert Is a Dead End for Template Defaults

Setting variables on the project via `variableUpsert` GraphQL mutation (with macro values like `${{secret(64)}}`) appears to succeed, but `templateGenerate` still produces NONE for those variables. The backend resolves/strips values between the upsert and generation steps. **Confirmed dead end — don't waste time on this approach.**

### Per-Service Template Files Are the Source of Truth

The local files (`plausible-ce.json`, `clickhouse/template-editor-raw.json`, etc.) are what get pasted into the dashboard editor. They should be maintained as the canonical source of variable defaults:

```
<template>/
├── template-vars.json              # Pipeline source (defaultValue, isOptional)
├── template-editor-raw.json        # Generated from template-vars.json
├── plausible-ce.json               # → Paste into Plausible CE Raw JSON
├── clickhouse/
│   ├── template-vars.json          # Companion pipeline source
│   └── template-editor-raw.json    # → Paste into ClickHouse Raw JSON
└── plausible-postgres.json         # → {} (plugin-managed)
```

### Per-Service Raw JSON = Variables Only

**The per-service Raw JSON editor in the dashboard only accepts environment variables.** It does NOT accept `source`, `deploy`, `volumeMounts`, `icon`, or any other service-level config.

These service-level settings must be configured through the dashboard **UI widgets** for each service tile:

| Setting | Where to Configure |
|---------|-------------------|
| `rootDirectory` | Service tile → Settings → Source → Root Directory |
| `volumeMounts` | Service tile → Add Volume → Mount Path + Size |
| `source` (repo/image) | Service tile → Settings → Source |
| `healthcheckPath` | Service tile → Settings → Healthcheck |
| `restartPolicy` | Service tile → Settings → Deploy |

**Symptom of confusion:** Pasting a full service JSON (with source/deploy/volumeMounts) into the per-service Raw JSON fails silently or is rejected. The editor ONLY stores the `variables` key.

**The root-level Raw JSON** (template-wide, not per-service) DOES accept `buckets` and the full `services` structure — but per-service Raw JSON is variables-only.

### Dashboard UI Widgets Don't Apply to Marketplace Deploys

**Settings configured via dashboard UI widgets do NOT propagate to marketplace deploys.** Confirmed:

| Setting | UI Widget | Applies to Deploy? |
|---------|-----------|:---:|
| `rootDirectory` | Service tile → Settings → Source → Root Directory | ❌ Confirmed |
| `volumeMounts` | Service tile → Add Volume → Mount Path + Size | ❌ (inferred) |
| `icon` | Service tile → icon URL field | ❌ (inferred) |

**The ONLY way to set these for marketplace deploys** is in the **root-level Raw JSON** (the full `serializedConfig`). The per-service Raw JSON only accepts variables, and the UI widgets don't persist to the template definition used during deploys.

**Symptom:** ClickHouse built from root Dockerfile (Plausible CE) because `rootDirectory` was set via UI widget but `serializedConfig` showed `null`. App crashes with `BASE_URL configuration option is required` — a Plausible error in the ClickHouse service.

## Pitfall: `${{Postgres.DATABASE_URL}}` Resolves Empty with `railway up`

**Symptom:** App crashes because DATABASE_URL is empty, even though Postgres plugin is running.

**Root cause:** `${{...}}` macros do NOT resolve during `railway up` deployments. They only work in template marketplace deploys. The Postgres plugin's own `DATABASE_URL` may also be empty when queried.

**Fix:** Construct DATABASE_URL from Postgres component vars:

```bash
# Get component vars
railway variables --service <postgres-id> --kv
# → POSTGRES_USER=postgres
# → POSTGRES_PASSWORD=xxx
# → RAILWAY_PRIVATE_DOMAIN=postgres.railway.internal
# → POSTGRES_DB=railway

# Construct and set:
railway variables set --service <app-id> \
  "DATABASE_URL=postgresql://postgres:xxx@postgres.railway.internal:5432/railway"
```

**Component var reference:**
- `POSTGRES_USER` — database user (usually `postgres`)
- `POSTGRES_PASSWORD` — auto-generated password
- `RAILWAY_PRIVATE_DOMAIN` — internal DNS (usually `postgres.railway.internal`)
- `POSTGRES_DB` — database name (usually `railway`)
- Format: `postgresql://$USER:$PASS@$HOST:5432/$DB`

**This applies to ALL `railway up` deployments, not just Plausible.** Template macros (`${{RAILWAY_PUBLIC_DOMAIN}}`, `${{secret(N)}}`, `${{Postgres.*}}`, `${{clickhouse.*}}`) ALL resolve to empty with `railway up`. Use concrete values for CLI deploys.

## Marketplace Deploy: Macro Resolution Matrix (2026-07-08)

Confirmed across three deploy tests (positive-kindness, divine-laughter, hospitable-wisdom):

| Macro | Resolves? |
|-------|:---:|
| `${{RAILWAY_PUBLIC_DOMAIN}}` | ✅ Domain only (no protocol) |
| `${{secret(N)}}` | ✅ Generates random value |
| `${{Postgres.DATABASE_URL}}` | ❌ Empty string |
| `${{Postgres.POSTGRES_*}}` | ❌ Empty string |
| `${{clickhouse.CLICKHOUSE_*}}` | ❌ Empty string |

**Key insight:** Only template-native macros (`RAILWAY_PUBLIC_DOMAIN`, `secret`) resolve. Cross-service references (Postgres plugin vars, ClickHouse companion vars) ALL resolve to empty. This is not a Postgres-specific limitation — it affects EVERY cross-service reference.

## Marketplace Deploy Issues: Three Persistent Template Bugs (2026-07-08)

These three issues happen on EVERY marketplace deploy from templates with Postgres + ClickHouse + companion services. Confirmed across three deploy tests (positive-kindness, divine-laughter, hospitable-wisdom).

### 1. `${{RAILWAY_PUBLIC_DOMAIN}}` Resolves Without `https://`

**Symptom:** Plausible CE crashes with `** (RuntimeError) BASE_URL configuration option required` when BASE_URL is `${{RAILWAY_PUBLIC_DOMAIN}}` — the macro resolves to just the domain without protocol.

**Confirmed template fix:** Use `https://${{RAILWAY_PUBLIC_DOMAIN}}` as the default. **Verified working in marketplace deploy** (hospitable-wisdom test — BASE_URL resolved to `https://plausible-ce-production-2557.up.railway.app` correctly).

**Post-deploy fix:**
```bash
railway variables set --service "Plausible CE" "BASE_URL=https://$FULL_DOMAIN"
```

### 2. `${{Postgres.DATABASE_URL}}` Resolves to Empty String

**Symptom:** DATABASE_URL is empty on the deployed Plausible CE service, causing DB connection failures and `(DBConnection.ConnectionError)` crashes during migration.

**Root cause:** The `${{Postgres.DATABASE_URL}}` macro does NOT resolve during marketplace deploys. The Postgres plugin's env vars are NOT auto-populated by the system in template deploys — confirmed by the user.

**Potential template fix (UNTESTED):** Set Postgres variables directly in the Postgres service's template Raw JSON with a KNOWN password, then hardcode the matching DATABASE_URL on the main service:
```json
// Postgres service Raw JSON:
{
  "POSTGRES_PASSWORD": { "value": "plausible2026", "description": "Superuser password" },
  "POSTGRES_DB": { "value": "railway", "description": "Default database" },
  "POSTGRES_USER": { "value": "postgres", "description": "Superuser" }
}

// Plausible CE Raw JSON:
{
  "DATABASE_URL": {
    "value": "postgresql://postgres:plausible2026@postgres.railway.internal:5432/railway",
    "description": "PostgreSQL connection URL"
  }
}
```
**Why both sides must match:** Don't use `${{secret(24)}}` for POSTGRES_PASSWORD — the random value can't be referenced from Plausible's DATABASE_URL since cross-service macros don't resolve. Use the same literal password on both services.

**Caveat:** Unclear whether the Postgres plugin accepts template form variables to override its auto-generated password. If it ignores them, the post-deploy fix (below) is still required.

**Post-deploy fix (confirmed working):** Create a sibling PostgresDB with known password — keep the broken plugin (deletion can cascade into PGDATA corruption):
```bash
# 1. Create PostgresDB service: serviceCreate with image: postgres:16-alpine
# 2. Set variables on new service: POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_USER
# 3. Set DATABASE_URL: postgresql://postgres:<password>@postgresdb.railway.internal:5432/railway
```

**WARNING:** NEVER use `variableUpsert` to set `POSTGRES_PASSWORD` on an existing Postgres plugin. This corrupts the PGDATA path and crashes Postgres.

### 3. `CLICKHOUSE_DATABASE_URL` Missing User:Password Credentials

**Symptom:** Plausible CE crashes with `Authentication failed: password is incorrect, or there is no user with such name` when connecting to ClickHouse as user `default`.

**Root cause:** The template form's default `CLICKHOUSE_DATABASE_URL=http://clickhouse:8123/plausible` has no user:password authentication. **The `${{clickhouse.CLICKHOUSE_USER}}:${{clickhouse.CLICKHOUSE_PASSWORD}}` companion references also resolve to empty in marketplace deploys** (same platform limitation as `${{Postgres.*}}`).

**No template-level fix exists** — companion service variable references don't resolve in marketplace deploys. The hardcoded URL is equally broken (connects as `default` user). The only working approach is post-deploy manual intervention:

```bash
# Get ClickHouse credentials
railway variables --service ClickHouse --kv  # get CLICKHOUSE_USER, CLICKHOUSE_PASSWORD
# Set the connection URL with actual credentials
railway variables set --service "Plausible CE" \
  "CLICKHOUSE_DATABASE_URL=http://$USER:$PASS@clickhouse:8123/plausible"
```

| Issue | Template Fixable? | Post-Deploy Fix |
|-------|:--:|-----------------|
| BASE_URL missing https:// | ✅ Use `https://` prefix (confirmed) | `railway variables set BASE_URL=https://...` |
| DATABASE_URL empty | ⚠️ Set Postgres vars in form (untested) | Create PostgresDB with known password |
| CLICKHOUSE_DATABASE_URL no creds | ❌ `${{clickhouse.*}}` resolves empty too | Get creds from ClickHouse service vars |