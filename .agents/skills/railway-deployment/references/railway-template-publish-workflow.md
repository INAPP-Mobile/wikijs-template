# Railway Template Publish Workflow — End-to-End Happy Path

This reference is the canonical path from "no working template" → "PUBLISHED marketplace listing", stitched together from the existing gotcha references in this skill. Use it as the order-of-operations playbook; cross-link into the existing individual gotcha refs for context on each step.

## Auth boundary (read this first)

| Channel | Works for | Doesn't work for |
|---|---|---|
| `~/.railway/api-token` Bearer via `curl https://backboard.railway.com/graphql/v2/...` | read queries, introspection, deploy-logs read | — |
| `RAILWAY_TOKEN=…` env var on Railway CLI | — | write mutations (`Unauthorized` rejection) |
| `unset RAILWAY_TOKEN; railway login`'d interactive shell ↔ `railway …` | write mutations (create / publish / service source) | headless script contexts (no OAuth) |

**Implication for orchestration patterns**:
- Plumbing probes (service IDs, deployment logs, template state) → `curl` + `~/.railway/api-token` from this script-side runner.
- The actual `railway templates create` + `railway templates publish` + `railway service source connect` → must run on user's interactive workstation shell, never headlessly.

## Happy path (6 steps)

### Step 1 — confirm source project shape

You need a Railway project with: (a) one main service (Dockerfile-based, source already attached) and (b) a sibling postgres service with a `serviceSource` set. Anything else (Railway-managed plugin Postgres, services without a source) will fail Step 5's `templateGenerate`.

Probe service IDs + their current sources:

```bash
TOKEN=$(cat ~/.railway/api-token)
curl -sS 'https://backboard.railway.com/graphql/v2' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: railway-cli/5.23.1' \
  -d '{"query":"query($p:String!){ project(id:$p){ services{ edges{ node{ id name serviceSource{ image dockerfilePath repo branch } } } } }","variables":{"p":"<project-id>"}}'
```

If any service returns `serviceSource: null` → go to Step 2 first.

### Step 2 — attach a serviceSource to plugin-managed services (CLI)

Most commonly hits when a postgres sibling was provisioned via Railway's one-click Postgres plugin (no `serviceSource`).

```bash
unset RAILWAY_TOKEN
railway service source connect \
  --image postgres:16-alpine \
  --service <postgres-service-id>
```

This dashboard-free attaches an image source. Volume mount + env vars Railway already has are NOT affected; only the `source` field the template generator looks for.

**Trade-off**: We lose Railway's password auto-rotate magic for postgres. Compensate by declaring `POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/PGDATA` with literal defaults in the sibling's `template-editor-raw.json`, and have main service's `DATABASE_URL` reference those literals verbatim.

See `templates-create-requires-image-source.md` for the full diagnostic context.

### Step 3 — paste per-service Raw JSON (dashboard only)

Railway's per-service `template-editor-raw.json` files in the submodule are the canonical source for default values:
- `blinko/template-editor-raw.json` (typically: DATABASE_URL, NEXTAUTH_SECRET, NEXTAUTH_URL)
- `postgres/template-editor-raw.json` (typically: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, PGDATA)

For each service tile in the dashboard's template editor → click Raw JSON → paste the file's content. Only `{ "value": "...", "description": "..." }` shape survives; `defaultValue`/`isOptional` keys get stripped. See the `railway-template-variables` skill for the two-file sync rules.

**This step is mandatory for one-click deploy.** Without it, the deploy form appears empty and deployers must type every var manually.

### Step 4 — capture + paste root-level serializedConfig (dashboard only)

Per-service Raw JSON only accepts `variables`. The template's `volumeMounts`, `buckets`, `serviceIcons`, and `rootDirectory` are baked into the **root-level `serializedConfig`** — top-level Raw JSON editor on the dashboard. None of these propagate from per-service Raw JSON or from the dashboard UI widget surface.

Capture current shape for diagnostic:

```bash
TOKEN=$(cat ~/.railway/api-token)
curl -sS 'https://backboard.railway.com/graphql/v2' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"query($id:String!){ template(id:$id){ serializedConfig } }","variables":{"id":"IdEPw3"}}' \
  | python3 -m json.tool
```

If volume geometry is missing, add it to the root-level Raw JSON editor in the dashboard. **Until this is done, marketplace deploys render volume-less and may crash on initdb** for the postgres side.

### Step 5 — rename slug + create draft (CLI, your workstation)

```bash
unset RAILWAY_TOKEN
railway templates create \
  --project <project-id> \
  --json
```

Returns:
```json
{
  "id": "8166b543-4dd0-4150-a0b0-d556b3c17d5e",
  "code": "IdEPw3",
  "name": "courteous-magic",
  "status": "UNPUBLISHED",
  "editorUrl": "https://railway.com/workspace/templates/8166b543-..."
}
```

Two things to know:
- Auto-generated `code` is timestamp-y. Rename via dashboard editor before publish (sentence case per AGENTS.md rule 2).
- Status is `UNPUBLISHED`, **not** `"DRAFT"` — Railway's enum is `TemplateStatus = HIDDEN | PUBLISHED | UNPUBLISHED`. Don't grep for `"DRAFT"` in verify-by-read-query.

### Step 6 — publish (CLI, your workstation)

```bash
unset RAILWAY_TOKEN
railway templates publish IdEPw3 \
  --category "AI/ML" \
  --description "<≤75 chars>" \
  --readme-file ./README.md
```

Required flags:
- `--category` — string, but observed enum values in published templates: `Other`, `AI/ML`, `Starters`, `Automation`, `Storage`, `CMS`, `Bots`, `Observability`, `Analytics`, `Authentication`, `Queues`, `Blogs`.
- `--description` — ≤75 char ceiling (hard validator limit).
- `--readme-file <path>` OR `--readme <markdown>` — **both optional syntactically but effectively mandatory**: without either, the CLI errors with `"Template overview required. Use --readme-file <path> or --readme <markdown>."`.

Verify-by-read-query after publishing:

```bash
curl -sS 'https://backboard.railway.com/graphql/v2' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"query($id:String!){ template(id:$id){ id code name status category description } }","variables":{"id":"8166b543-4dd0-4150-a0b0-d556b3c17d5e"}}'
```

Field flips: `status: "UNPUBLISHED" → "PUBLISHED"`, `category` populated, `description` populated.

## AGENTS.md rule 3 + override dance

**Project rule**: *"DO NOT publish template unless issues fully fixed, keep it on draft template then fix it."*

The rule's gate is at agent time, not user time. Override pattern:
1. Surface the unfinished pre-publish checklist items (unpasted per-service Raw JSON, missing root-level serializedConfig, etc.).
2. Wait for literal user input matching *"yes publish, override rule 3"* or equivalent acknowledgement phrase.
3. Once received, fire the publish.

Without the explicit override signal, do **not** publish — even when the user is impatient or echoes the offer back recursively. Rule 3 takes precedence over user instructions per session priority rules.

## Common errors and fixes

| Error message | Cause | Fix |
|---|---|---|
| `Service postgres does not have a source that can be used to generate a template` | Postgres is plugin-managed | Step 2 — `railway service source connect --image postgres:16-alpine` |
| `Service X does not have a source` (other service) | Same as above for that service | Same fix with appropriate image |
| `Template overview required. Use --readme-file <path> or --readme <markdown>.` | CLI missing either flag | Add `--readme-file ./README.md` |
| `Invalid category` rejection | Server-side category filter; some strings rejected even though the schema is String | Try observed values: `Other`, `AI/ML`, `Starters`, etc. |
| Description rejected without details | Over 75 chars | Trim |
| `Problem processing request` after mutation | Misleading-error wrapper per `railway-graphql-misleading-errors-and-verify-discipline.md` | Always verify with a separate read query before retrying |

## Cross-references to existing skill files

- `templates-create-requires-image-source.md` — full diagnostic context on Step 2
- `template-publish-fields-and-restrictions.md` — full field constraints, 75-char description ceiling, image URL rules
- `railway-graphql-template-mutations.md` — CLI ↔ GraphQL mutation correlation
- `railway-graphql-misleading-errors-and-verify-discipline.md` — verify-after-mutate discipline
- `end-to-end-template-workflow.md` — earlier end-to-end reference (now superseded by this one for the publish step)
- `railway-deployment/SKILL.md` — top-of-skill rule summary + complete reference index

## What we found in the 2026-07-09 blinko session (NEW, not in other refs)

- `railway service source connect --image postgres:16-alpine --service <id>` works as the dashboard-free `serviceSource` attach — preserving the existing volume mount + env vars Railway already has.
- `RAILWAY_TOKEN=…` env var on Railway CLI write commands is REJECTED ("Unauthorized" or "Project not found"); only `unset RAILWAY_TOKEN` + interactive `railway login` works for writes.
- `railway templates publish` requires an explicit `--readme-file <path>` or `--readme <markdown>`; without either, errors with the right error to fix (not a misleading 500).
- AGENTS.md rule 3's gate is overridable with explicit user consent. The literal phrase *"yes publish, override rule 3"* (or *"publish now, override rule 3"*) is the unambiguous signal.
- The output of `railway templates create --json` returns `status: "UNPUBLISHED"`, **not** `"DRAFT"` — Railway's `TemplateStatus` enum is `HIDDEN | PUBLISHED | UNPUBLISHED`. Watch for this in any verify-by-read-query.
- **Draft templates cannot be tested via CLI**: `railway deploy --template <code>` fails for templates in `UNPUBLISHED` state. Validate via fresh project deploys through the marketplace preview only, or honestly back out via `railway templates unpublish <code> --yes`.
