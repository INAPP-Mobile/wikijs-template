# Template Variables via serializedConfig — Working Automation (2026-06-29)

## Summary

Template variables CAN be set programmatically via the Railway GraphQL API by modifying the `serializedConfig` JSON blob and calling `templateDeployV2`. This contradicts the earlier assumption (pitfalls #23, #30) that template variables are dashboard-only.

## Discovery

Railway's `serializedConfig` is a custom scalar (JSON blob) stored on each template. It has the structure:

```json
{
  "buckets": {},
  "services": {
    "<service-uuid>": {
      "icon": null,
      "name": "service-name",
      "deploy": { ... },
      "source": { "repo": "...", "rootDirectory": null },
      "variables": {
        "VAR_NAME": {
          "isOptional": false,
          "defaultValue": "...",
          "description": "..."
        }
      }
    }
  }
}
```

The `templateDeployV2` mutation accepts:
- `templateId: String!`
- `serializedConfig: SerializedTemplateConfig!` (the full JSON blob)
- `projectId: String`
- `environmentId: String`
- `workspaceId: String`

## Working Script

`/var/home/ihshim523/Work/railway/scripts/railway-graphql.py`

### Commands

```bash
# List all templates
python3 railway-graphql.py list

# Query a template's current config
python3 railway-graphql.py query <template_id>

# Update variables (reads manifest, injects into serializedConfig, deploys)
python3 railway-graphql.py update-vars <template_id> <vars_json_file>

# Deploy with current config (no changes)
python3 railway-graphql.py deploy <template_id>

# Publish template
python3 railway-graphql.py publish <template_id> <category> <description> <readme_path>
```

### Variable Manifest Format

The `vars_json_file` for `update-vars` uses this format:

```json
{
  "PORT": {
    "defaultValue": "8080",
    "description": "Application port",
    "isOptional": false
  },
  "API_KEY": {
    "defaultValue": "",
    "description": "Optional API key",
    "isOptional": true
  }
}
```

## Critical: User-Agent Header

Railway's API sits behind Cloudflare. Requests without a `User-Agent` header get HTTP 403 error code 1010 (Cloudflare challenge), even with a valid token. Always include:

```python
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "User-Agent": "railway-cli/5.23.1",  # Required!
}
```

## API Introspection Method

To discover this, we introspected the GraphQL schema:

```graphql
# Get mutation fields
{ __schema { mutationType { fields { name args { name type { name kind ofType { name } } } } } } }

# Get Template type fields
{ __type(name: "Template") { fields { name type { name kind ofType { name } } } } }

# Get TemplateDeployV2Input
{ __type(name: "TemplateDeployV2Input") { inputFields { name type { name kind ofType { name } } } } } }
```

Key findings:
- `Template` has `serializedConfig` field (returns the JSON blob)
- `TemplateDeployV2Input.serializedConfig` is `NON_NULL<SerializedTemplateConfig>`
- `SerializedTemplateConfig` is a SCALAR — not introspectable (opaque JSON)
- No dedicated `templateVariableSet` mutation exists
- `variableUpsert` / `variableCollectionUpsert` operate on service/environment runtime vars only (require `projectId` + `environmentId`)

## Pipeline Integration

The pipeline flow changed from:

```
Old: deploy → set runtime vars → templates create (0 vars) → configure vars in DASHBOARD → publish
New: deploy → set runtime vars → templates create (0 vars) → railway-graphql.py update-vars → publish
```

See `pipeline-bodies/deploy-publish.txt` for the updated agent instructions.

## Auth Token Format

Both token formats work for GraphQL:
- Account Token: `railway_...` (from railway.com/account/tokens)
- Session Token: hex UUID like `68a16d92-beea-476a-bfdc-de522b6ba517` (from `~/.railway/api-token`)

The critical requirement is the `User-Agent` header, NOT the token format.
