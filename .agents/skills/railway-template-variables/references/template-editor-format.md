# Template Editor: Variable Format, File Splitting & Lifecycle

Session-derived patterns for working with the Railway template editor's Raw JSON view.

## Editor Variable Format

The template editor validates variables as `{ "value": string, "description": string }`.
It does **not** accept `defaultValue`, `isOptional`, or bare strings.

### Correct format

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

### Incorrect formats (will fail validation)

```json
// FAIL: defaultValue + isOptional (GraphQL serializedConfig format)
{
  "BASE_URL": {
    "defaultValue": "${{RAILWAY_PUBLIC_DOMAIN}}",
    "isOptional": false,
    "defaultValue": "${{RAILWAY_PUBLIC_DOMAIN}}"
  }
}

// FAIL: bare string
{
  "BASE_URL": "${{RAILWAY_PUBLIC_DOMAIN}}"
}
```

**Error pasting wrong format:** `JSON values must be strings or { value: string, description?: string | null }`

### Converting GraphQL `templateGenerate` output to editor format

`templateGenerate` returns:
```json
{
  "BASE_URL": { "defaultValue": "${{RAILWAY_PUBLIC_DOMAIN}}", "isOptional": false },
  "SECRET_KEY_BASE": { "defaultValue": "${{secret(64)}}", "isOptional": false },
  "DISABLE_REGISTRATION": { "isOptional": true }
}
```

After editor paste + save:
- `${{...}}` expressions survive as `${{RAILWAY_PUBLIC_DOMAIN}}`, `${{secret(64)}}`
- Literal values (`false`, `http://clickhouse:8123/plausible`) get **stripped**

**Fix:** When pasting `templateGenerate` output into the editor, manually include literal defaults as `"value"` strings:
```json
{
  "DISABLE_REGISTRATION": { "value": "false", "description": "..." },
  "CLICKHOUSE_DATABASE_URL": { "value": "http://clickhouse:8123/plausible", "description": "..." }
}
```

## Per-Service JSON File Splitting

When the full `services` block is too large for terminal copy-paste, create per-service files
containing **only the `variables` object** each service needs:

**Sibling-service layout (current 2026-07-08):**
```
railway-plausible/
├── plausible-ce.json             # → Plausible CE service variables
├── clickhouse/template-editor-raw.json      # → ClickHouse tile variables
└── postgres/template-editor-raw.json        # → Postgres sibling tile variables (postgres:16-alpine)
```

**Legacy plugin layout (deprecated 2026-07-08; postgres-ssl:18 crashed on lost+found):**
```
railway-plausible/
├── plausible-ce.json
├── clickhouse.json
└── plausible-postgres.json       # → {} (plugin-managed, delete the plugin first)
```

`plausible-ce.json`:
```json
{
  "BASE_URL": { "value": "${{RAILWAY_PUBLIC_DOMAIN}}", "description": "Public URL for Plausible" },
  "DATABASE_URL": { "value": "${{plausible-postgres.DATABASE_URL}}", "description": "Postgres connection URL (auto-injected)" },
  "SECRET_KEY_BASE": { "value": "${{secret(64)}}", "description": "Cookie signing secret (64-char random)" },
  "DISABLE_REGISTRATION": { "value": "false", "description": "Set to true to disable public registration" },
  "CLICKHOUSE_DATABASE_URL": { "value": "http://clickhouse:8123/plausible", "description": "ClickHouse connection URL" },
  "ENABLE_EMAIL_VERIFICATION": { "value": "false", "description": "Set to true to require email verification" }
}
```

`clickhouse.json`:
```json
{
  "CLICKHOUSE_DB": { "value": "plausible", "description": "ClickHouse database name" },
  "CLICKHOUSE_USER": { "value": "plausible", "description": "ClickHouse user" },
  "CLICKHOUSE_PASSWORD": { "value": "${{secret(24)}}", "description": "ClickHouse password (24-char random)" }
}
```

`plausible-postgres.json`:
```json
{}
```

**Usage:** Paste each file's content into the matching service's `variables` key in the Raw JSON editor.

## Template Lifecycle via CLI

All commands are non-interactive / headless safe:

```bash
# List workspace templates
railway templates list --json

# Create draft from project
railway templates create --project <project-id> --json
# Output: { "id": "...", "code": "...", "name": "...", "status": "UNPUBLISHED" }

# Delete draft
railway templates delete <template-id> --yes

# Publish (requires user confirmation)
railway templates publish <code> --category "Analytics" --description "..." --readme-file README.md

# Unpublish
railway templates unpublish <code> --yes
```

## Template Rename Workflow

No `templateUpdate` GraphQL mutation exists. Template name is locked at generation time.

```bash
# 1. Rename the project (GraphQL)
curl -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { projectUpdate(id: \"...\", input: { name: \"New Name\" }) { id name } }"}'

# 2. Delete old draft
railway templates delete <old-template-id> --yes

# 3. Regenerate
railway templates create --project <project-id> --json
```

**Note:** `railway projects rename` CLI command may not exist in all versions. Use GraphQL `projectUpdate(id: ..., input: { name: ... })`.

## Auth Token for GraphQL

Read from `~/.railway/config.json` → `user.accessToken`. Tokens expire — re-auth via `railway login --browserless` if CLI returns "Unauthorized".
