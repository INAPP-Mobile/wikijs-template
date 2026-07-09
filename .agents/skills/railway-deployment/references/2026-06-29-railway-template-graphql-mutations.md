# 2026-06-29 — Railway Template GraphQL Mutations Reference

## Template Mutations Discovered

### `templatePublish` — Create or Update Template

```graphql
mutation TemplatePublish($id: String!, $input: TemplatePublishInput!) {
  templatePublish(id: $id, input: $input) {
    id
    code
    name
    readme
    image
    category
    description
    status
    workspace { id name }
  }
}
```

**Input: `TemplatePublishInput`**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `category` | String | Yes | e.g., "Other", "Starters", "Analytics", "Bots", "CMS", "Storage", "Queues", "AI/ML", "Authentication", "Automation", "Blogs", "Observability" |
| `description` | String | Yes | Short marketplace description |
| `image` | String | No | Raw SVG/PNG URL (must be `https://raw.githubusercontent.com/...`) |
| `readme` | String | Yes* | Full markdown content (escaped JSON string) |
| `workspaceId` | String | Yes | Target workspace ID |
| `demoProjectId` | String | No | Public demo project ID |

*Required for first publish; optional for updates.

**Notes:**
- Works for both initial publish AND updates (if template already exists, it's an update)
- Can use either template `code` (e.g., `stirling-pdf-1`) or template `id` (UUID) as the `$id` argument
- Returns updated template object

### `templateClone` — Clone Existing Template

```graphql
mutation TemplateClone($input: TemplateCloneInput!) {
  templateClone(input: $input) {
    id
    code
    name
  }
}
```

**Input: `TemplateCloneInput`**
| Field | Type | Required |
|-------|------|----------|
| `code` | String | Yes |
| `workspaceId` | String | Yes |

### `templateDelete` — Delete Template

```graphql
mutation TemplateDelete($id: String!, $input: TemplateDeleteInput!) {
  templateDelete(id: $id, input: $input) {
    success
  }
}
```

**Input: `TemplateDeleteInput`**
| Field | Type | Required |
|-------|------|----------|
| `workspaceId` | String | Yes |

### `templateUnpublish` — Unpublish (Keep in Dashboard)

```graphql
mutation TemplateUnpublish($id: String!) {
  templateUnpublish(id: $id) {
    success
  }
}
```

### `templateDeployV2` — Deploy Template to Project

```graphql
mutation TemplateDeployV2($input: TemplateDeployV2Input!) {
  templateDeployV2(input: $input) {
    projectId
    environmentId
    services { edges { node { id name } } }
  }
}
```

**Input: `TemplateDeployV2Input`**
| Field | Type | Required |
|-------|------|----------|
| `templateId` | String | Yes |
| `projectId` | String | Yes |
| `environmentId` | String | Yes |
| `serializedConfig` | SerializedTemplateConfig | Yes |
| `workspaceId` | String | Yes |

### `templateGenerate` — Generate Template from Project

```graphql
mutation TemplateGenerate($input: TemplateGenerateInput!) {
  templateGenerate(input: $input) {
    id
    code
    name
  }
}
```

**Input: `TemplateGenerateInput`**
| Field | Type | Required |
|-------|------|----------|
| `projectId` | String | Yes |
| `environmentId` | String | Yes |

### `templateServiceSourceEject` — Eject Template Source

```graphql
mutation TemplateServiceSourceEject($input: TemplateServiceSourceEjectInput!) {
  templateServiceSourceEject(input: $input) {
    success
  }
}
```

**Input: `TemplateServiceSourceEjectInput`**
| Field | Type | Required |
|-------|------|----------|
| `projectId` | String | Yes |
| `repoOwner` | String | Yes |
| `repoName` | String | Yes |
| `upstreamUrl` | String | Yes |
| `serviceIds` | [String!]! | Yes |

### `serviceCreate` — Create Service in Project

```graphql
mutation ServiceCreate($i: ServiceCreateInput!) {
  serviceCreate(input: $i) {
    id
    name
  }
}
```

**Input: `ServiceCreateInput`**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | String | Yes | Service name |
| `projectId` | String | Yes | Target project ID |
| `source` | ServiceSourceInput | Yes | Source config (repo or image) |
| `branch` | String | No | Default branch |
| `environmentId` | String | No | Target environment |
| `icon` | String | No | Service icon URL |
| `registryCredentials` | RegistryCredentialsInput | No | For private registries |
| `templateId` | String | No | Template to deploy |
| `templateServiceId` | String | No | Template service to copy |
| `variables` | EnvironmentVariables | No | Initial env vars |

**Input: `ServiceSourceInput`**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `repo` | String | No | GitHub repo (format: `owner/repo`) |
| `image` | String | No | Docker image URL |

**CRITICAL:** The repo URL must be wrapped in a `source` object: `{source: {repo: "owner/repo"}}`. Passing `repo` directly at the top level of `ServiceCreateInput` fails with "Problem processing request". The `branch` field inside `source` may be required for some repos.

### `variableCollectionUpsert` — Set Service Variables

```graphql
mutation VariableCollectionUpsert($i: VariableCollectionUpsertInput!) {
  variableCollectionUpsert(input: $i) {
    success
  }
}
```

**Input: `VariableCollectionUpsertInput`**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `projectId` | String | Yes | |
| `serviceId` | String | Yes | |
| `environmentId` | String | Yes | |
| `variables` | [VariableInput!] | Yes | List of `{key, value}` objects |
| `replace` | Boolean | No | Replace all (true) vs merge (false) |

### `projectCreate` — Create Project

```graphql
mutation ProjectCreate($i: ProjectCreateInput!) {
  projectCreate(input: $i) {
    id
    name
  }
}
```

**Input: `ProjectCreateInput`**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | String | Yes | Project name |
| `workspaceId` | String | Yes | Target workspace |

### `projectDelete` — Delete Project

```graphql
mutation ProjectDelete($id: String!) {
  projectDelete(id: $id)
}
```

---

## GraphQL Endpoint & Auth

- **Endpoint:** `https://backboard.railway.com/graphql/v2`
- **Auth Header:** `Authorization: Bearer <ACCOUNT_TOKEN>` (format: `railway_...`)
- **Project Token Header:** `Project-Access-Token: <PROJECT_TOKEN>` (for project-scoped ops only)

---

## cURL Example: Update Template README

```bash
# Get README content (properly escaped for JSON)
README=$(cat README.md | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

# Execute mutation
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"mutation TemplatePublish(\\$id: String!, \\$input: TemplatePublishInput!) { templatePublish(id: \\$id, input: \\$input) { id code name readme image } }\",\"variables\":{\"id\":\"dce8dc2c-5b88-4a84-8fe5-c4f1dad58ddb\",\"input\":{\"category\":\"Other\",\"description\":\"Self-hosted PDF tool with 50+ tools, zero dependencies, 84K★.\",\"image\":\"https://raw.githubusercontent.com/INAPP-Mobile/railway-stirling-pdf/main/template-icon.svg\",\"readme\":\"$README\",\"workspaceId\":\"b82233e8-ff27-4ca9-9a30-a7411337a2d9\"}}}"
```

---

## Introspection Queries (for discovering new mutations)

```bash
# All template-related mutations
curl -s -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { mutationType { fields { name args { name type { name kind ofType { name kind } } } } } } }"}' \
  https://backboard.railway.com/graphql/v2 | jq '.data.__schema.mutationType.fields[] | select(.name | test("template"; "i"))'

# TemplatePublishInput fields
curl -s -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { types { name kind inputFields { name type { name kind ofType { name kind ofType { name kind } } } } } } }"}' \
  https://backboard.railway.com/graphql/v2 | jq '.data.__schema.types[] | select(.name == "TemplatePublishInput")'
```