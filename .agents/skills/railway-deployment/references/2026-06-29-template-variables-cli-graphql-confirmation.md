# 2026-06-29 — Template Variable Configuration: CLI & GraphQL Confirmation

## Session Summary
User asked if there's a CLI command to update env variables for templates. Investigation confirmed: **no such command exists**.

## Checks Performed

### CLI Commands Checked
```bash
railway templates --help          # Only: create, publish, update, list, search, delete, unpublish
railway variable --help           # Only works on project services, not template drafts
railway template --help           # Same as railway templates
```

**Result**: No `railway templates variable ...` subcommand exists.

### GraphQL Mutations Checked
- `templatePublish` — accepts only metadata: `category`, `description`, `image`, `readme`, `workspaceId`, `demoProjectId`
- `templateGenerate` — creates draft from project (captures vars but doesn't configure them)
- No `templateVariableSet`, `templateVariableUpdate`, `templateVariableConfig` mutations found

### Documentation Check
- `llms-full.txt` (Railway docs) — no mention of programmatic template variable configuration
- Template creation docs emphasize web dashboard composer for variable editing

## Confirmed Workflow (Unchanged)

| Step | Tool | Can Configure Variables? |
|------|------|--------------------------|
| Create draft | `railway templates create` | ❌ Captures current values only |
| Configure vars | **Web Dashboard → Template Composer** | ✅ Required/Optional, Default, Description, `secret()` |
| Publish | `railway templates publish` / `templatePublish` mutation | ❌ Metadata only |

## For Agent Pipelines

The **Development agent (Build Railway Template)** must include an explicit manual step:

```markdown
## After template draft created:

⚠️ MANUAL STEP REQUIRED (no automation available):
1. Open: https://railway.com/workspace/templates
2. Click your draft template
3. Go to **Variables** tab
4. For each service/variable:
   - Toggle **Required** ✅/❌
   - Set **Default** (use `{{secret(32)}}` for secrets)
   - Add **Description**
5. Click **Save** → then proceed to E2E testing
```

## Related References
- `references/2026-06-29-template-variable-config-dashboard.md` — Full dashboard workflow
- `references/2026-06-29-railway-template-graphql-mutations.md` — GraphQL mutation reference