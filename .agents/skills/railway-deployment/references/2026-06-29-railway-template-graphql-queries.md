# Railway Template GraphQL Queries — Schema & Field Reference

Source: Live introspection at `https://backboard.railway.com/graphql/v2` (2026-06-29)

## Key Discovery: Query Names

`templateByCode` does **NOT** exist as a query. Use `template(code: "xxx")` instead.

```
# ❌ Does not exist:
query { templateByCode(code: "xxx") { id name } }

# ✅ Correct query — use code, id, owner, or repo:
query { template(code: "xxx") { id name code image } }
```

## Template Query Fields

### Single Template Lookup: `template`

```graphql
query {
  template(code: String, id: String, owner: String, repo: String) {
    id
    code
    name
    image              # Icon URL for marketplace card (null = default Railway icon)
    description         # Short marketplace description (≤75 chars)
    category            # Marketplace category string
    readme              # Full markdown (may be truncated in some responses)
    status              # "PUBLISHED", "UNPUBLISHED", "DRAFT"
    isVerified          # Boolean — verified by Railway partner program
    isApproved          # Boolean — approved status
    isV2Template        # Boolean — v2 template format
    supportHealthMetrics # Boolean
    totalPayout         # Number — total kickback earnings
    projects            # Number — deployment count
    activeProjects      # Number — currently active deployments
    recentProjects      # Number — recent deployments
    createdAt           # ISO timestamp
    updatedAt           # ISO timestamp
    creator { id name } # Template creator user
    workspaceId         # Workspace UUID
    tags                # Array of tag strings
    languages           # Array of language strings
    health              # Health status object
    services            # Array of service configs
    serializedConfig    # JSON blob (scalar type)
    similarTemplates    # Array of related templates
    communityThreadSlug # Central Station thread slug
    demoProjectId       # Demo project UUID
    guides              # Array of guide links
    canvasConfig        # Canvas layout config
    maintainer { id name } # Partner program maintainer
    recentProjects      # Recent deployment metrics
    services            # Service definitions array
  }
}
```

### List Templates: `templates`

```graphql
query {
  templates(
    first: Int,        # Page size (max 50 tested)
    after: String,     # Cursor for pagination
    before: String,
    last: Int,
    recommended: Boolean,  # Filter to recommended
    verified: Boolean      # Filter to verified only
  ) {
    edges {
      node {
        id code name image creator { name } status
        # ... all Template fields
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

**Important:** The `templates` query returns ALL published templates on the marketplace, not just your own. Use `workspaceTemplates(workspaceId: "...")` to scope to your workspace.

### Search Templates: `templateSearch`

```graphql
query {
  templateSearch(
    query: String,     # Search text
    verified: Boolean, # Filter to verified only
    category: String,  # Filter by category
    first: Int,
    after: String,
    before: String,
    last: Int
  ) {
    edges {
      node { id code name image description creator { name } }
    }
  }
}
```

### Workspace Templates: `workspaceTemplates`

```graphql
query {
  workspaceTemplates(
    workspaceId: String!,
    first: Int,
    after: String,
    before: String,
    last: Int
  ) {
    edges { node { id code name image status } }
  }
}
```

### Template Metrics: `templateMetrics`

```graphql
query {
  templateMetrics(id: String!) {
    # Returns metrics for a specific template
    # (no further schema info available — query and inspect)
  }
}
```

### Other Template-Related Queries

| Query | Args | Purpose |
|-------|------|---------|
| `templateSourceForProject(projectId: String!)` | projectId | Source info linked to a project |
| `templatesCount` | (none) | Total count of published templates |
| `sandboxTemplateBuild(environmentId: String!, id: String!)` | environmentId, id | Sandbox build status |

## Field Reference: `Template` Type

| Field | Type | Notes |
|-------|------|-------|
| `id` | ID! | UUID |
| `code` | String | Marketplace slug (e.g. `stirling-pdf-1`) |
| `name` | String | Display name |
| `image` | String | Raw GitHub URL to icon. **null means default Railway icon** |
| `description` | String | Short marketplace description |
| `category` | String | Marketplace category |
| `readme` | String | Full markdown README |
| `status` | String | PUBLISHED / UNPUBLISHED / DRAFT |
| `isVerified` | Boolean | Partner program verified badge |
| `isApproved` | Boolean | Approval status |
| `isV2Template` | Boolean | Uses v2 template format |
| `totalPayout` | Float | Kickback earnings total |
| `projects` | Int | Deployment count |
| `activeProjects` | Int | Currently active |
| `creator` | User | Creator user object |
| `workspaceId` | String | Owning workspace UUID |
| `tags` | [String] | Tags array |
| `languages` | [String] | Languages array |
| `serializedConfig` | JSON (scalar) | Opaque JSON config blob |
| `services` | [TemplateService] | Service definitions |
| `similarTemplates` | [TemplateSummary] | Related templates |
| `createdAt` | DateTime | Timestamp |
| `updatedAt` | DateTime | Timestamp |

## Auth Requirements

| Query | Auth Required | Notes |
|-------|-------------|-------|
| `template(code:)` | No* | Public read access for published templates |
| `templates(first:)` | No* | Lists all marketplace templates |
| `templateSearch(query:)` | No* | Public search |
| `workspaceTemplates` | Yes | Requires workspace membership |
| `templateMetrics` | Yes | Requires ownership |
| `__type(name:)` | No | Public introspection |
| `__schema { }` | No | Public introspection |

*Without auth, some queries return HTTP 400 when they need user context. The distinction: queries that return data about the marketplace are public; queries that require a specific user/workspace are not.

## Practical Examples

### Check if a Template Has a Custom Icon (CLI one-liner)

```bash
python3 -c "
import json, urllib.request
q = {'query': '{ templates(first: 100) { edges { node { code name image } } } }'}
req = urllib.request.Request('https://backboard.railway.com/graphql/v2',
  data=json.dumps(q).encode(),
  headers={'Content-Type': 'application/json', 'User-Agent': 'railway-cli/5.23.1'})
data = json.loads(urllib.request.urlopen(req).read())
for e in data['data']['templates']['edges']:
  n = e['node']
  print(f'{n[\"code\"]:30s} | icon: {n.get(\"image\", \"NONE\") or \"NONE\"}')
"
```

### Find Templates Without Icons

```bash
python3 -c "
import json, urllib.request
q = {'query': '{ templates(first: 100) { edges { node { code name image } } } }'}
req = urllib.request.Request('https://backboard.railway.com/graphql/v2',
  data=json.dumps(q).encode(),
  headers={'Content-Type': 'application/json', 'User-Agent': 'railway-cli/5.23.1'})
data = json.loads(urllib.request.urlopen(req).read())
missing = [e['node'] for e in data['data']['templates']['edges'] if not e['node'].get('image')]
print(f'Missing icons ({len(missing)}):')
for n in missing:
  print(f'  {n[\"code\"]:30s} — https://railway.com/deploy/{n[\"code\"]}')
"
```

### Get Own Template Details (with auth)

```python
tok = open(os.path.expanduser('~/.railway/api-token')).read().strip()
q = {'query': '{ template(code: "railway-n8n") { id code name image creator { name } workspaceId } }'}
req = urllib.request.Request('https://backboard.railway.com/graphql/v2',
  data=json.dumps(q).encode(),
  headers={
    'Authorization': 'Bearer ' + tok,
    'Content-Type': 'application/json',
    'User-Agent': 'railway-cli/5.23.1'
  })
data = json.loads(urllib.request.urlopen(req).read())
```

### Discover All Template Query Fields

```graphql
query {
  __type(name: "Template") {
    fields { name type { name kind ofType { name kind } } }
  }
}
```

## See Also

- `references/2026-06-29-railway-template-graphql-mutations.md` — Mutation-side API (publish, delete, deploy, etc.)
- `references/2026-06-29-railway-auth-env-var-debugging.md` — Auth troubleshooting (env var override, token types)
- `references/2026-06-29-graphql-cloudflare-user-agent.md` — User-Agent header requirement for Cloudflare
