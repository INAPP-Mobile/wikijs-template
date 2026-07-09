# 2026-06-29 — Service Variables vs Template Variables: Full CLI + GraphQL Automation Available

## Session Summary
User asked "how about service variables?" after learning that template variables cannot be automated via CLI alone. Key finding: **service variables are fully automatable via CLI**, and **template variables can now be automated via serializedConfig + templateDeployV2** (GraphQL API).

## The Critical Distinction

| Concept | Scope | CLI Automation | GraphQL Automation | Who Configures | When |
|---------|-------|----------------|---------------------|----------------|------|
| **Template Variables** | Template draft (deploy-time prompts) | ❌ CLI only | ✅ serializedConfig + templateDeployV2 | Template author | Between `templates create` and `templates publish` |
| **Service Variables** | Running project service env vars | ✅ Full CLI support | ✅ variableCollectionUpsert | Anyone with project access | Anytime after service exists |

## Template Variables: Automated (serializedConfig Approach)

Template variables are stored in the `serializedConfig` JSON blob at `services[id].variables`. They can be injected via GraphQL:

```bash
python3 railway-graphql.py update-vars <template_id> vars_manifest.json
```

Manifest format:
```json
{
  "PORT": {"defaultValue": "8080", "description": "App port", "isOptional": false}
}
```

**Limitations vs dashboard:** Cannot set `${{secret()}}` or `${{randomInt()}}` functions — those remain dashboard-only.

See `references/2026-06-29-template-vars-via-serialized-config.md` for full guide.

## Service Variable CLI Commands

```bash
# List all variables for a service
railway variable list -s <service> --json
railway variable list -s <service> --kv  # raw values

# Set a variable
railway variable set KEY=value -s <service> --skip-deploys
railway variable set KEY=value -s <service> -e <environment> --skip-deploys

# Set secret from stdin (avoids shell history exposure)
echo "secret" | railway variable set KEY --stdin -s <service> --skip-deploys

# Delete a variable
railway variable delete KEY -s <service>

# All commands accept -p <project> and -e <environment> flags
```

## Pipeline Implications

### Full Automation Flow (2026-06-29)
```bash
# 1. Set runtime service vars (CLI)
python3 set-service-vars.py <project_id> <env_id> vars_manifest.json

# 2. Create template draft (0 template vars initially)
railway templates create --project <project_id> --environment production --json

# 3. Inject template variables via GraphQL (no dashboard needed)
python3 railway-graphql.py update-vars <template_id> vars_manifest.json

# 4. Publish
railway templates publish <template_id> --category "Other" --description "..." --readme-file README.md
```

### Option A: Capture from Source Project (When Vars Already Set)
If the template is created from an existing project via `railway templates create --project <id>`, the project's current env vars are captured into the template draft automatically. Then use `update-vars` to add descriptions/required toggles.

### Option B: Set After Deploy (End-User Responsibility)
The deploying user sets variables on their own project after deploying your template.

## For Agent Pipeline Bodies

When writing deploy-body.txt for a template pipeline, include:

```markdown
### Service Variables (CLI-automatable)
- Set required env vars on the deploy project:
  railway variable set KEY=value -s <service> --skip-deploys

### Template Variables (GraphQL-automatable)
- Inject via serializedConfig + templateDeployV2:
  python3 railway-graphql.py update-vars <template_id> vars_manifest.json
- For secret/random functions: configure in web dashboard
```

## Related References
- `references/2026-06-29-template-vars-via-serialized-config.md` — Full automation guide
- `references/2026-06-29-template-variable-config-dashboard.md` — Dashboard workflow (still works)
- `references/2026-06-29-graphql-cloudflare-user-agent.md` — Cloudflare UA requirement
