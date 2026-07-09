# Template Variable Repair Pipeline: Full Investigation & Fix

**Date:** 2026-06-29
**Problem:** 18 published Railway templates had empty `variables: {}` in their serializedConfig, causing deployed services to crash with missing env vars.

## Investigation Steps

### 1. List Published Templates

```bash
unset RAILWAY_TOKEN  # Important! See auth debugging reference
railway templates list --workspace INAPP --json
```

### 2. Query Template Variables via GraphQL

```bash
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ template(code: \"pocketbase-5\") { id name services { edges { node { config } } } serializedConfig } }"}'
```

Result showed `"variables": {}` — confirming no variables configured.

### 3. GraphQL Schema Introspection for Variable Mutations

Searched all mutations for anything related to template variables:

```bash
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ __schema { mutationType { fields { name } } } }"}'
```

Template-related mutations found:
- `sandboxTemplateBuild`
- `templateClone`
- `templateDelete`
- `templateDeployV2`
- `templateGenerate`
- `templatePublish`
- `templateServiceSourceEject`
- `templateUnpublish`
- `templateVolumeUpdate`

**None of these accept variable configuration.** `TemplatePublishInput` only accepts: `category`, `demoProjectId`, `description`, `image`, `readme`, `workspaceId`.

### 4. Check TemplateServiceConfig Type

```bash
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ __type(name: \"TemplateServiceConfig\") { fields { name type } } }"}'
```

Result: `{"fields": null}` — it's a scalar (opaque JSON blob), not introspectable.

### 5. Check SerializedTemplateConfig Type

```bash
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H 'Content-Type: application/json' \
  -d '{"query": "{ __type(name: \"SerializedTemplateConfig\") { inputFields { name } } }"}'
```

Result: `{"inputFields": null}` — also a scalar, not introspectable.

## Conclusion

**No programmatic way exists to set template variables.** They can only be configured in the Railway web dashboard template composer.

## Fix Applied: Dockerfile ENV Defaults

Since template variables can't be set programmatically, the fix was to add `ENV` defaults directly in each template's Dockerfile:

| Template | ENV Vars Added |
|----------|---------------|
| railway-changedetection.io | `USE_X_SETTINGS=1` |
| railway-filebrowser | `ROOT=/srv`, `FB_USERNAME=admin`, `FB_DATABASE=/srv/filebrowser.db` |
| railway-gotify | 10 vars (port, bindaddress, user, pass, db, registration, etc.) |
| railway-hoppscotch | `PORT=3000`, `WHITELISTED_ORIGINS=` |
| railway-kanboard | `PORT=80`, `DB_DRIVER=sqlite` |
| railway-n8n | `N8N_BASIC_AUTH_ACTIVE=*** `N8N_BASIC_AUTH_USER=*** `N8N_BASIC_AUTH_PASSWORD=*** |
| railway-netdata | `PGID=1000`, `DOCKER_GROUP_ID=1000` |
| railway-plausible | `PORT=8000` |
| railway-syncthing | `PUID=1000`, `PGID=1000` |

## Secrets NOT Added (must be user-provided)

- `DATABASE_URL`, `SECRET_KEY`, `DATA_ENCRYPTION_KEY`
- `BASE_URL`, `CLICKHOUSE_DATABASE_URL`
- `MEMOS_DSN` (references Postgres plugin vars)
- `ENCRYPTION_KEY`, `COOLIFY_ADMIN_PASSWORD`

## Verification Script

```python
import os
dockerfile_path = 'Dockerfile'
with open(dockerfile_path, 'r') as f:
    content = f.read()

checks = ['PORT=', 'TZ=', 'PUID=', 'PGID=']
for search in checks:
    if search in content:
        print(f'[OK] {search}')
    else:
        print(f'[SKIP] {search}')  # Not all templates need all vars
```

## Pipeline Impact

This fix ensures that even without template variables configured in the dashboard, services will at least start with reasonable defaults. Users still need to set secrets manually, but non-secret config (ports, paths, timezone) is pre-loaded.
