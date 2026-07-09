# Railway Template Variable Configuration — Now Automated via serializedConfig

## UPDATE (2026-06-29): Dashboard is NO Longer Required

**Previous assumption:** Template variables could only be configured in the Railway web dashboard template composer.

**New finding:** Template variables are stored in the `serializedConfig` JSON blob and CAN be set programmatically via `templateDeployV2`. The dashboard is still an option but no longer required.

## The Two Approaches

### Approach A: serializedConfig + templateDeployV2 (Automated, Preferred)

1. Create template draft via CLI (0 variables)
2. Inject variables into serializedConfig via GraphQL
3. Call `templateDeployV2` with updated config
4. Re-publish

```bash
# Inject variables
python3 railway-graphql.py update-vars <template_id> vars_manifest.json

# Then publish
railway templates publish <template_id> --category "Other" --description "..." --readme-file README.md
```

See `references/2026-06-29-template-vars-via-serialized-config.md` for the full guide.

### Approach B: Web Dashboard (Manual, Still Works)

| Step | Where | What Happens |
|------|-------|--------------|
| **1. Create template draft** | CLI: `railway templates create` | Creates draft with 0 template variables |
| **2. Configure variables** | **Web Dashboard → Template Composer** | Edit variables: descriptions, required/optional, `secret()` functions |
| **3. Publish** | CLI or Dashboard | Publish to marketplace |

### Variable Manifest Format (for Automation)

```json
{
  "PORT": {
    "defaultValue": "8080",
    "description": "Application port",
    "isOptional": false
  }
}
```

### Template Variable Functions (Dashboard Only — NOT via serializedConfig)

- `${{secret(length?, alphabet?)}` — generates random secrets (default 32 chars)
- `${{randomInt(min?, max?)}` — random integers

These **cannot be set via serializedConfig** — they remain dashboard-only. The serializedConfig approach handles `defaultValue`, `description`, and `isOptional` only.

### Related References

- `references/2026-06-29-template-vars-via-serialized-config.md` — Full automation guide
- `references/2026-06-29-graphql-cloudflare-user-agent.md` — Cloudflare UA requirement
- `references/2026-06-29-railway-template-graphql-mutations.md` — Full GraphQL mutation reference