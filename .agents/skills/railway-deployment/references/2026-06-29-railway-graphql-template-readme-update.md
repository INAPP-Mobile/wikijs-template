# 2026-06-29 — Railway GraphQL Template README Update

## Context

Session discovered that Railway's GraphQL API allows updating published template metadata (README, image, description, category) via the `templatePublish` mutation — no CLI required. This enables CI/CD pipelines and agents to fix template metadata headlessly.

## Discovery

Queried Railway's GraphQL endpoint (`https://backboard.railway.com/graphql/v2`) to find mutations related to templates. Found `templatePublish` which accepts `TemplatePublishInput` with `readme`, `image`, `description`, `category`, and `category` fields.

The mutation works for **both initial publish AND updates** — if the template already exists (by code or UUID), it updates it.

## GraphQL Schema

### Mutation

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

### Input: `TemplatePublishInput`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `category` | String | Yes | Valid: `AI/ML`, `Analytics`, `Authentication`, `Automation`, `Blogs`, `Bots`, `CMS`, `Observability`, `Other`, `Starters`, `Storage`, `Queues` |
| `description` | String | Yes | Max 75 chars |
| `image` | String | No | Raw GitHub URL: `https://raw.githubusercontent.com/owner/repo/branch/template-icon.svg` |
| `readme` | String | Yes* | Full markdown, JSON-escaped. Required for initial publish; optional for updates. |
| `workspaceId` | String | Yes | Target workspace UUID |
| `demoProjectId` | String | No | Public demo project ID |

*Required for first publish; optional for updates.

## Authentication

**MUST use Account Token** (`railway_...` from https://railway.com/account/tokens)

- Session token (UUID from `~/.railway/config.json`) does NOT work
- Account token is non-expiring
- Header: `Authorization: Bearer railway_...`

## cURL Example (Update README)

```bash
# Read README and JSON-escape it
README=$(cat TEMPLATE.md | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer railway_..." \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"mutation TemplatePublish(\\$id: String!, \\$input: TemplatePublishInput!) { templatePublish(id: \\$id, input: \\$input) { id code name readme image category description status } }\",\"variables\":{\"id\":\"stirling-pdf-1\",\"input\":{\"category\":\"Other\",\"description\":\"Self-hosted PDF tool with 50+ tools, zero dependencies, 84K★.\",\"image\":\"https://raw.githubusercontent.com/INAPP-Mobile/railway-stirling-pdf/main/template-icon.svg\",\"readme\":\"$README\",\"workspaceId\":\"b82233e8-ff27-4ca9-9a30-a7411337a2d9\"}}}"
```

## Template ID Format

The `id` argument accepts either:
- Template **code** (e.g., `stirling-pdf-1`, `plausible-2`)
- Template **UUID** (from `templates create` or `templates list --json`)

## Related Files

- `references/2026-06-29-railway-template-graphql-mutations.md` — Full mutation reference
- `references/2026-06-29-stirling-pdf-deploy-button-fix.md` — Deploy button URL fix case study