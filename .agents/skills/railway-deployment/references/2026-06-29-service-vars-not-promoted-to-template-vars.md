# Service Vars Are NOT Auto-Promoted to Template Vars

**Date:** 2026-06-29
**Status:** Proven with live testing

## Claim (DISPROVED)

> Setting `railway variable set` on a deployed project, then running `railway templates create`, auto-captures those vars as template variables.

## Reality

Template variables and service environment variables are **completely separate systems**. `railway templates create` generates a template with the service structure (Dockerfile, start command, volumes, source repo) but **0 template variables**, regardless of what env vars are set on the project.

## Reproduction

```bash
# 1. Set vars on the deployed project
railway variable set GENERIC_TIMEZONE=UTC \
  --project 8ff43b94 --environment 9f78e931 \
  --skip-deploys --json
# → {"keys":["GENERIC_TIMEZONE"],"set":true}

# 2. Verify vars exist on the project
railway variable list --project 8ff43b94 --environment 9f78e931 --json
# → {"GENERIC_TIMEZONE":"UTC", ...}

# 3. Create template from the project
railway templates create --project 8ff43b94 --environment 9f78e931 --json
# → {"id": "81f2ceb4-...", "name": "railway-n8n", ...}

# 4. Check template vars
railway templates list --workspace INAPP --json
# → vars: 0   ← NO template variables captured
```

## What Each System Does

| System | Set By | Scope | Purpose |
|--------|--------|-------|---------|
| Service env vars | `railway variable set` / GraphQL `variableCollectionUpsert` | Runtime on a specific deployed service | Service starts with correct configuration |
| Template variables | Dashboard template editor ONLY | Deploy-time prompts when a user deploys from the template | Users configure their own instances |

## What Automation Exists

- **Service env vars:** Fully automatable via CLI (`railway variable set`) and GraphQL (`variableCollectionUpsert`)
- **Template variables:** Dashboard-only. No CLI command, no GraphQL mutation. `TemplatePublishInput` doesn't include variable fields. `TemplateServiceConfig` is an opaque scalar.

## Impact on Pipeline

1. `set-service-vars.py` is still useful — sets runtime vars so the deployed service works
2. Template variable config must happen in the dashboard (manual or browser automation)
3. The "variable gate" in deploy-publish.txt checks template var count — if 0, block with editor link
