# `railway templates create` Requires Docker Image Source

The CLI command `railway templates create --project <id>` fails when the project's services were deployed via `railway up` (Dockerfile build) rather than from a pre-built Docker image.

## Symptom

```
$ railway templates create --project plausible-verify --json
Service plausible-verify does not have a source that can be used to generate a template
```

## Why

Railway templates capture a Docker image reference (registry path + tag). When you deploy via `railway up`, Railway builds the image internally but doesn't expose it as a reusable "source" that the template system can reference. The template system needs a proper image source — either:
- An image pushed to a registry (Docker Hub, GHCR, etc.)
- A project that was initially created from an image source

## Two Paths to Create a Draft Template

### Path A: CLI (requires image source)

Only works if the service already has a Docker image source. Check first:

```bash
railway service list --json | python3 -c "
import sys,json
data=json.load(sys.stdin)
for s in data:
    print(s['name'], '→ source:', s.get('source'))
"
```

If `source` is `null`, CLI path won't work. You must either:
1. Push your image to a registry and set it as the service source
2. Or use Path B below

### Path B: Dashboard (no image source needed)

The Railway dashboard's "Generate Template" action can create a template from any deployed project, regardless of source type.

1. Open project in Railway dashboard: `https://railway.com/project/<id>`
2. Click "Generate Template" action
3. Railway creates an unpublished draft
4. Configure variables in template editor
5. Publish when ready

**Note:** Dashboard access may require authenticated session — the browser tool often hits bot detection. In that case, use `railway login --browser` to establish auth, or ask the user to create the draft manually.

### Path C: GitHub Source (CLI workaround — no dashboard needed)

**Discovered 2026-07-08.** Connecting a GitHub repo as the service source gives the service a proper source reference, enabling `railway templates create` via CLI without dashboard access or registry push.

```bash
# 1. Create fresh project
railway init --name <name> --json   # capture project ID
cd <repo-dir>
railway link --project <id>

# 2. Deploy local code (validates TOML + Dockerfile build)
railway up --detach --json

# 3. Connect GitHub repo as the service source
railway service source connect --repo <owner>/<repo> --branch main --service <name> --json
#   → source now shows the repo, not null

# 4. NOW CLI template creation works
railway templates create --json
#   → returns template id, code, editorUrl, status=UNPUBLISHED
```

The editor URL from step 4 opens the template editor where you configure:
- Display name, description, category
- Deploy form variables (BASE_URL, SECRET_KEY_BASE, etc.)
- Icon, README, demo project

**Crashing is fine** — template draft creation works even if the service crashes on startup (e.g. missing env vars). The form configuration is independent of app health.

## CRITICAL: CLI Template Creation Produces EMPTY Variables

**Discovered 2026-07-08.** When you create a template via CLI `railway templates create`, the resulting template's `serializedConfig.services.<id>.variables` comes back **empty** — even if `template-vars.json` exists in the repo. The CLI does NOT read `template-vars.json` or `template-editor-raw.json` from the repo.

```bash
# Check template variables via GraphQL:
TOKEN=$(cat ~/.railway/config.json | python3 -c "import sys,json; print(json.load(sys.stdin)['user']['accessToken'])")
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { template(id: \"<ID>\") { serializedConfig } }"}' \
  | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['data']['template']['serializedConfig'], indent=2))"
```

You'll see `"variables": {}` for services that should have form vars.

### Workaround A: Reuse Old Published Template (preferred when available)

If a previous version of the template exists and was published with correct variables, **unpublish it to convert to draft** instead of creating new:

```bash
# Find old template (may not show in `railway templates list` if archived)
# Query via GraphQL or check publish-record.json for old template IDs
railway templates unpublish <old-code> --yes --json
# → Now it's an UNPUBLISHED draft with variables already configured
```

The old template's `serializedConfig` already has variables properly set (including auto-resolved service references like `${{Postgres.DATABASE_URL}}`). No need to reconfigure.

### Workaround B: Configure Variables in Dashboard

After CLI creation, open the `editorUrl` and manually configure variables through the Railway dashboard template editor. The editor reads template-vars.json from the repo when you open it.

### Variable Resolution Patterns

Railway template variables use these auto-resolution patterns:
- `${{secret(64)}}` — auto-generate 64-byte random string
- `${{RAILWAY_PUBLIC_DOMAIN}}` — auto-set from Railway public domain
- `${{Postgres.DATABASE_URL}}` — auto-resolve from linked Postgres service
- `${{clickhouse.CLICKHOUSE_USER}}` — auto-resolve from linked ClickHouse service
- `http://${{clickhouse.CLICKHOUSE_USER}}:${{clickhouse.CLICKHOUSE_PASSWORD}}@clickhouse:8123/${{clickhouse.CLICKHOUSE_DB}}` — composite ClickHouse URL

### Path D: Push Image, Then Create Template

If you must use a pre-built image (not GitHub source):

```bash
# 1. Build and tag image locally
podman build -t ghcr.io/your-org/plausible-ce:latest .

# 2. Push to registry
podman push ghcr.io/your-org/plausible-ce:latest

# 3. Set as service source
railway service source connect --image ghcr.io/your-org/plausible-ce:latest --service <name>

# 4. Now CLI works
railway templates create --project <id> --json
```

## Key Takeaway

When fixing a broken template that was previously published:
1. Fix the root cause (TOML syntax, Dockerfile CMD, etc.)
2. Push the fix to git
3. Create a NEW project with the fixed code (old template is gone)
4. Deploy via `railway up` to verify build succeeds
5. Draft template via dashboard (since CLI needs image source)
6. Delete test projects when done
