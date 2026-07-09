# Config as Code vs Infrastructure as Code (IaC)

**Key discovery 2026-07-08:** Railway has TWO code-based configuration systems with different scopes.

| System | Scope | File | Multi-service? |
|--------|-------|------|----------------|
| Config as Code | ONE service's build/deploy config | `railway.json` or `railway.toml` | **NO** — only one `[build]`/`[deploy]` block |
| Infrastructure as Code | Entire project: services, DBs, volumes, variables | `.railway/railway.ts` (TypeScript) | **YES** |

## The Critical Limitation

A `railway.toml` like this does NOT create two services:

```toml
[[services]]
name = "plausible"

[services.plugins.postgresql]

[[services]]
name = "clickhouse"

[services.build]
dockerfilePath = "clickhouse/Dockerfile"
```

Railway's Config as Code parser reads the file as a **single service** config. The `[[services]]` array syntax is ignored or causes parse ambiguity — only ONE service gets created (typically the first one, or whichever has the `[build]`/`[deploy]` blocks).

## When to Use Which

**Use Config as Code (`railway.toml`/`railway.json`) when:**
- Single-service project (most common)
- You only need to override build/start/healthcheck for one service

**Use IaC (`.railway/railway.ts`) when:**
- Multi-service project (app + postgres + clickhouse, etc.)
- Need plugins (PostgreSQL, Redis, etc.)
- Need volumes and volume mounts
- Need to define variables at project level
- Need buckets, custom domains, canvas groups

## IaC Example (Multi-Service with Plugins)

After `railway config init`, edit `.railway/railway.ts`:

```typescript
import {
  defineRailway, github, postgres, project, service, volume
} from "railway/iac";

export default defineRailway(() => {
  const db = postgres("plausible-postgres");
  const chData = volume("clickhouse-data", {
    region: "us-west2", sizeMB: 10240,
  });

  const plausible = service("plausible-ce", {
    source: github("INAPP-Mobile/railway-plausible", { branch: "main" }),
    healthcheck: "/api/health",
    healthcheckTimeout: 60,
    env: {
      DATABASE_URL: db.env.DATABASE_URL,
      CLICKHOUSE_DATABASE_URL: "http://clickhouse:8123/plausible",
    },
  });

  const clickhouse = service("clickhouse", {
    source: github("INAPP-Mobile/railway-plausible", {
      branch: "main", rootDirectory: "clickhouse",
    }),
    healthcheck: "/ping",
    healthcheckTimeout: 30,
    volumeMounts: { "/var/lib/clickhouse": chData },
  });

  return project("plausible", {
    resources: [plausible, clickhouse, db, chData],
  });
});
```

Then apply:
```bash
railway config plan
railway config apply
```

## IaC SDK Installation Gotcha

The Railway IaC SDK (`railway` npm package) must be installed in the project for the CLI to evaluate `.railway/railway.ts`:

```bash
# May time out on slow connections — retry with longer timeout
npm install github:railwayapp/railway-ts-sdk
```

**KNOWN ISSUE:** The Railway CLI's embedded Node may not resolve the installed SDK, causing:
```
Could not find Railway configuration support for this project.
Install the Railway TypeScript SDK, then run this command again.
```

If this persists, use the **GraphQL API approach** instead (see `references/railway-graphql-template-introspection.md`). The GraphQL path avoids IaC entirely by calling `serviceCreate`, `serviceInstanceUpdate`, and `templateGenerate` mutations directly.

## Migration Notes

- A service CANNOT be managed by both systems simultaneously.
- `railway config plan` will error if services still have `railway.json`/`railway.toml` defining them.
- To migrate: `railway config pull --force` then remove `railway.toml`.

## Template Implications

When creating a draft template from a project that uses **IaC**:
1. `railway config apply` creates all services + plugins in the project
2. Deploy each service (they will likely crash without env vars — that's fine)
3. `railway templates create` captures all services into the draft
4. Configure variables in the template editor

**Alternative (GraphQL path):** Build the project via `serviceCreate` + `serviceInstanceUpdate` mutations, then `templateGenerate`. Then open the editor URL to finalize metadata. See `references/railway-graphql-template-introspection.md` for the full recipe.
