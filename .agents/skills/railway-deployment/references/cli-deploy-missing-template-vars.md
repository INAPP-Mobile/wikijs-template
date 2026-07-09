# CLI `railway up` Does NOT Inject Template Vars

When testing a Railway template locally via `railway up`, the build may succeed but the app still crashes on startup with healthcheck failures. Root cause: **template vars (BASE_URL, SECRET_KEY_BASE, DATABASE_URL, etc.) are ONLY injected when deploying through the Railway template UI URL** (`/deploy/<code>`), NOT when running `railway up` from the CLI.

## Symptom Pattern

1. `railway.toml` syntax is valid (build succeeds, image pushes)
2. Healthcheck reaches `/api/health` but gets "service unavailable" on every retry
3. `1/1 replicas never became healthy!`
4. The app inside the container immediately crashes because required env vars are empty

## Why

Template vars like these in `template-editor-raw.json`:
```json
{
  "BASE_URL": { "value": "${{RAILWAY_PUBLIC_DOMAIN}}" },
  "SECRET_KEY_BASE": { "value": "${{secret(64)}}" }
}
```

…are part of the template manifest, NOT the project file. `railway up` reads `railway.toml` (service structure + build config) but NOT the template deploy-form vars. Those get resolved server-side only when you deploy via the template marketplace URL.

## Fix Paths

### Option A: Manual var injection for CLI testing

```bash
# Set all required vars manually before deploy
railway variables --service <svc> --set "BASE_URL=https://your-domain.com"
railway variables --service <svc> --set "SECRET_KEY_BASE=$(openssl rand -base64 48)"
railway variables --service <svc> --set "DATABASE_URL=postgresql://user:pass@host:5432/db"
railway variables --service <svc> --set "CLICKHOUSE_DATABASE_URL=http://clickhouse:8123/plausible"
```

Then `railway up` will deploy with those vars and the app should start.

### Option B: Deploy via template URL (full template injection)

1. Publish the template: `railway templates publish <code> --category "Analytics" --description "..." --readme-file README.md`
2. Open `https://railway.com/deploy/<code>` in browser
3. Fill out the form vars → Railway injects them automatically

## Plausible CE Required Vars

When deploying Plausible CE via CLI, set these explicitly:

| Var | Typical CLI value |
|-----|-------------------|
| `BASE_URL` | `https://your-domain.com` |
| `SECRET_KEY_BASE` | `$(openssl rand -base64 48)` |
| `DATABASE_URL` | From postgres plugin or `postgresql://user:pass@host:5432/db` |
| `CLICKHOUSE_DATABASE_URL` | `http://clickhouse:8123/plausible` |

## Template Variable Type Split

Template variables fall into two categories with different serializedConfig representations:

### 1. User-facing form vars (in template-vars.json)

```json
{
  "BASE_URL": {
    "defaultValue": "${{RAILWAY_PUBLIC_DOMAIN}}",
    "description": "Public URL. Auto-set from Railway public domain.",
    "isOptional": true
  },
  "SECRET_KEY_BASE": {
    "defaultValue": "${{secret(64)}}",
    "description": "64-byte random string. Auto-generated.",
    "isOptional": false
  }
}
```

These appear in the deploy form. `defaultValue` uses Railway template syntax:
- `${{RAILWAY_PUBLIC_DOMAIN}}` — Railway public domain
- `${{secret(N)}}` — auto-generate N-byte random string

### 2. Auto-resolved runtime vars (NOT in form)

```json
{
  "DATABASE_URL": {
    "isOptional": false,
    "description": "Auto-resolved from Postgres service",
    "defaultValue": "${{Postgres.DATABASE_URL}}"
  },
  "CLICKHOUSE_DATABASE_URL": {
    "isOptional": false,
    "description": "Auto-resolved from ClickHouse service",
    "defaultValue": "http://${{clickhouse.CLICKHOUSE_USER}}:${{clickhouse.CLICKHOUSE_PASSWORD}}@clickhouse:8123/${{clickhouse.CLICKHOUSE_DB}}"
  }
}
```

These are resolved at deploy time from linked services. They are NOT shown in the form.

**SerializedConfig format in `template.serializedConfig.services.<id>.variables`:**
```json
{
  "VAR_NAME": {
    "isOptional": false,
    "description": "Human-readable description",
    "defaultValue": "${{Postgres.DATABASE_URL}}"
  }
}
```

## User Correction: CLI Deploy IS Valid First Step

User: "There is way to deploy from github repo, would it work?"

**Yes.** The workflow is:
1. Fix root cause in repo (TOML syntax, Dockerfile, etc.) → push to GitHub
2. `railway init` → `railway link` → `railway up` (build validates)
3. `railway service source connect --repo <owner>/<repo>` (gives service a source)
4. `railway templates create` (CLI works now without dashboard)
5. Even if service crashes (missing vars), draft template creation succeeds
6. Open `editorUrl` to configure variables form

**User: "Do not publish template to market yet, just create draft."**

This is standard practice per AGENTS.md rule: keep as draft, fix all issues, verify with fresh deploy before publishing to marketplace. `railway templates publish` is irreversible (goes live to public marketplace) — only run after full verification.
