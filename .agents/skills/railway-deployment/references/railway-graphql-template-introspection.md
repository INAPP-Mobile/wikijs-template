# Railway GraphQL API: Template Introspection & Build

How to inspect AND build Railway templates via GraphQL API — dashboard-free, full control over multi-service templates.

## Authentication

```bash
# Token is in ~/.railway/api-token (one-line UUID file, NOT config.json)
TOKEN=$(cat ~/.railway/api-token)
```

## Endpoint

```
POST https://backbone.railway.app/graphql/v2
Headers:
  Authorization: Bearer $TOKEN
  Content-Type: application/json
```

**CORRECTION (2026-07-08):** Earlier versions of this doc claimed `templateGenerate` returns "Not Authorized" via API token. **This is false.** `templateGenerate` works fine with the `~/.railway/api-token`. We have successfully created templates with it.

## Python Helper

```python
import json, urllib.request

TOKEN = open("/var/home/ihshim523/.railway/api-token").read().strip()
ENDPOINT = "https://backbone.railway.app/graphql/v2"

def graphql(query, variables=None):
    data = {"query": query, "variables": variables or {}}
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
```

## Template Introspection

### List All Workspace Templates (including unpublished)

```python
q = """query {
  me {
    templates {
      edges { node { id code name status serializedConfig } }
    }
  }
}"""
```

### Get Template Serialized Config (Service Layout + Variables)

```python
q = """query ($id: ID!) {
  template(id: $id) {
    id code name status serializedConfig
  }
}"""
r = graphql(q, {"id": "<TEMPLATE_ID>"})
config = r["data"]["template"]["serializedConfig"]
for sid, svc in config["services"].items():
    print(f"=== {svc['name']} ===")
    print(f"  source: {svc.get('source',{})}")
    print(f"  variables: {list(svc.get('variables',{}).keys())}")
    print(f"  deploy: {svc.get('deploy',{})}")
```

### Schema Introspection (Discover Available Fields)

```python
# List Template type fields
q = """{ __type(name: "Template") { fields { name } } }"""

# Find mutations involving templates
q = """{ __type(name: "Mutation") { fields { name } } }"""
# Then filter: [f['name'] for f in data['data']['__type']['fields'] if 'template' in f['name'].lower()]
```

## Template SerializedConfig Structure

```json
{
  "buckets": {},
  "services": {
    "<service-uuid>": {
      "icon": null,
      "name": "service-name",
      "deploy": {
        "startCommand": null,
        "healthcheckPath": "/api/health",
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
      },
      "source": {
        "repo": "https://github.com/owner/repo",
        "rootDirectory": null
      },
      "variables": {
        "VAR_NAME": {
          "isOptional": false,
          "description": "Human-readable description",
          "defaultValue": "${{Postgres.DATABASE_URL}}"
        }
      },
      "volumeMounts": {
        "<service-uuid>": {
          "mountPath": "/var/lib/data"
        }
      }
    }
  }
}
```

## Build Multi-Service Template via GraphQL (Full Recipe)

This is the complete dashboard-free workflow for creating a multi-service template (app + postgres + clickhouse). Proven 2026-07-08.

### Step 1: Create Project

```python
create_proj = """mutation ($name: String!, $workspaceId: String!) {
  projectCreate(input: {name: $name, workspaceId: $workspaceId}) {
    id primaryEnvironmentId
  }
}"""
r = graphql(create_proj, {"name": "my-app", "workspaceId": "<WORKSPACE_ID>"})
project_id = r["data"]["projectCreate"]["id"]
env_id = r["data"]["projectCreate"]["primaryEnvironmentId"]
```

Get workspace ID from any existing project:
```python
q = """query { project(id: "<EXISTING_PROJECT_ID>") { workspace { id } } }"""
```

### Step 2: Create Services

```python
create_svc = """mutation ($input: ServiceCreateInput!) {
  serviceCreate(input: $input) { id name }
}"""

# Postgres (image source)
pg = graphql(create_svc, {"input": {
    "projectId": project_id, "environmentId": env_id,
    "name": "plausible-postgres",
    "source": {"image": "ghcr.io/railwayapp-templates/postgres-ssl:18"},
    "icon": "https://devicons.railway.app/i/postgresql.svg"
}})

# App (repo source)
app = graphql(create_svc, {"input": {
    "projectId": project_id, "environmentId": env_id,
    "name": "plausible-ce",
    "source": {"repo": "https://github.com/owner/repo"},
    "icon": "https://simpleicons.org/icons/plausibleanalytics.svg"
}})

# ClickHouse (repo source — rootDirectory comes later)
ch = graphql(create_svc, {"input": {
    "projectId": project_id, "environmentId": env_id,
    "name": "clickhouse",
    "source": {"repo": "https://github.com/owner/repo"},
    "icon": "https://devicons.railway.app/i/clickhouse.svg"
}})
```

**IMPORTANT:** `ServiceCreateInput.source` only accepts `image` and `repo` strings — NOT `rootDirectory`. You must set `rootDirectory` later via `serviceInstanceUpdate`.

### Step 3: Connect GitHub Sources (REQUIRED)

Creating a service with `source.repo` is NOT enough. You must also run the CLI `source connect` for each GitHub-sourced service, or `templateGenerate` fails with "Service X does not have a source that can be used to generate a template":

```bash
railway service source connect --repo owner/repo --branch main --service <SERVICE_ID> --json
```

### Step 4: Update Service Instances (rootDirectory, healthcheck)

```python
update_inst = """mutation ($serviceId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, input: $input)
}"""

# Set clickhouse rootDirectory + healthcheck
graphql(update_inst, {
    "serviceId": ch_id,
    "input": {
        "rootDirectory": "clickhouse",
        "healthcheckPath": "/ping",
        "healthcheckTimeout": 30,
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10,
    }
})

# Set app healthcheck
graphql(update_inst, {
    "serviceId": app_id,
    "input": {
        "healthcheckPath": "/api/health",
        "healthcheckTimeout": 60,
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10,
    }
})
```

**IMPORTANT:** `serviceInstanceUpdate` takes `serviceId` as a SEPARATE argument (not inside `input`). `ServiceUpdateInput` only accepts `icon` and `name` — cannot update deploy config.

### Step 5: Set Variables

Use the CLI (not GraphQL — `variableUpsert` via API is unreliable):

```bash
railway link --project <PROJECT_ID> --service <SERVICE_ID>
railway variable set KEY='value' --skip-deploys --json
```

**CRITICAL GOTCHA:** `templateGenerate` strips literal variable values. Only Railway-template-expression values survive as `defaultValue`:
- `${{RAILWAY_PUBLIC_DOMAIN}}` → kept as defaultValue
- `${{secret(64)}}` → kept as defaultValue
- `${{plausible-postgres.DATABASE_URL}}` → kept as defaultValue
- `false`, `plausible`, `http://clickhouse:8123/plausible` → STRIPPED (variable shows only `isOptional: false`)

To force a literal default, use a Railway expression or set it manually in the dashboard editor after generation.

### Step 6: Generate Template

```python
gen = """mutation ($input: TemplateGenerateInput!) {
  templateGenerate(input: $input) {
    id code name status serializedConfig
  }
}"""
r = graphql(gen, {"input": {"projectId": project_id, "environmentId": env_id}})
tmpl = r["data"]["templateGenerate"]
print(f"Template: {tmpl['name']} ({tmpl['code']}) — editor: https://railway.com/workspace/templates/{tmpl['id']}")
```

### Step 7: Cleanup

Delete stale templates via CLI (GraphQL `templateDelete` signature is finicky):
```bash
railway templates delete <TEMPLATE_ID> --yes
```

## Template Mutations Reference

| Mutation | Status | Notes |
|----------|--------|-------|
| `templateGenerate(input: {projectId, environmentId})` | WORKS | Creates template from project |
| `templateDelete(input: {id})` | WORKS but finicky | Use CLI `railway templates delete <id> --yes` for reliability |
| `templatePublish(id, input: {category, description, readme})` | WORKS | Requires category + readme |
| `templateUnpublish(id)` | WORKS | Converts published → draft |
| `templateClone(input: {code, workspaceId})` | WORKS | Clones existing template |
| `templateServiceSourceEject(input)` | WORKS | Removes source from template service |
| `templateVolumeUpdate(...)` | WORKS | Resize volume |

## Service Mutations Reference

| Mutation | Key Fields | Notes |
|----------|-----------|-------|
| `serviceCreate` | `projectId, environmentId, name, source: {image\|repo}, icon` | No rootDirectory |
| `serviceUpdate` | `icon, name` ONLY | Cannot update deploy config |
| `serviceInstanceUpdate(serviceId, input)` | `rootDirectory, healthcheckPath, healthcheckTimeout, restartPolicyType, source` | serviceId is separate arg |
| `variableCollectionUpsert` | `serviceId, variables` | Use CLI instead — more reliable |
| `variableUpsert` | `serviceId, name, value, environmentId` | Often returns "Problem processing request" |

## Limitations (Verified 2026-07-08)

- `templateGenerate` strips literal variable values (only `${{...}}` expressions survive)
- `ServiceCreateInput.source` does NOT accept `rootDirectory` — must use `serviceInstanceUpdate` after
- `railway service source connect` (CLI) is REQUIRED for GitHub-sourced services before `templateGenerate`
- `variableUpsert` via API is unreliable — use `railway variable set` CLI instead
- `templateDelete` via GraphQL has finicky signature — use `railway templates delete` CLI
- Dashboard template editor is still needed for: template name, description, category, icon, README, demo project
- `ServiceUpdateInput` only accepts `icon` and `name` — cannot update deploy config via mutation
