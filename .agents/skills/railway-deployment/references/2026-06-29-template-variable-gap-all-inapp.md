# 2026-06-29 — Template Variable Gap: All INAPP Templates Need Repair

## Problem

**All 19 INAPP-Mobile published templates have 0 environment variables configured.** This means:
- End-users deploy the template with NO prompts for required configuration
- No descriptions, no defaults, no `secret()` functions for sensitive values
- Services start with whatever is baked into the Dockerfile (or crash if vars are required)

Verification:
```bash
railway templates list --workspace INAPP --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for t in data:
    print(f\"{t['code']:30s} | vars: {len(t.get('variables',[]))}\")
"
# All output: vars: 0
```

## Comparison: What Good Looks Like

A well-configured template (e.g., `brody192/filebrowser-template`) shows:
- `WEB_USERNAME` — required field with description "Your own username for the login credentials"
- "2 Pre-Configured Environment Variables" — defaults, `secret()` for password
- Deploy UI presents input fields before deployment starts

**Our templates show none of this** — users get a raw deploy with no configuration step.

## Why This Happened

1. `railway templates create` captures service variables from source project values
2. But **template variable configuration** (required/optional toggle, descriptions, defaults) is **Dashboard-only**
3. The CLI has no flags for it; GraphQL `templatePublishInput` only accepts metadata
4. Our pipeline's `deploy-draft.txt` had a "MANUAL STEP REQUIRED" note but the manual step was never enforced
5. The Publish agent created+torett Published the draft without verifying variables were configured

## The Fix Pipeline

### Option A: Repair Existing Published Templates (Mass Repair)
For each template repo:
1. Read `.env.example` to identify required vars
2. Add `ENV` defaults directly to Dockerfile (safe non-secret values only)
3. Commit + push → Railway auto-rebuilds template
4. Re-publish via `railway templates publish <id>` to refresh marketplace
5. **Dashboard step still needed** for required/optional toggles + descriptions

### Option B: Prevent Future Gap (Pipeline Body Updates)
Update `deploy-draft.txt`:
- After `railway templates create`, MANDATE a dashboard variable config step
- Block the next card (Publish) until the user confirms variables are configured
- Add verification: agent checks if template has >0 variables before proceeding

Update `deploy-publish.txt`:
- Pre-publish check: query template variables count (if CLI ever supports it)
- Or: block until user manual confirmation

### Option C: Hybrid (Recommended)
1. **Immediate:** Add Dockerfile ENV defaults to all 19 template repos (safe values only)
2. **Pipeline fix:** Update `deploy-draft.txt` to include mandatory dashboard step with URL
3. **Verification:** `deploy-verify.txt` sets all required service vars before health check

## Template Variable Types

| Variable Type | Example | Safe to Default? | Dashboard Config Needed? |
|--------------|---------|------------------|-------------------------|
| Port numbers | `PORT=8080` | ✅ Yes | For description only |
| Paths | `ROOT=/srv` | ✅ Yes | For description only |
| Timezone | `TZ=UTC` | ✅ Yes | For description only |
| Username | `USER=admin` | ✅ Yes (non-secret) | For description |
| Passwords | `PASS=*** | ❌ No | Required (need `secret()`) |
| Database URL | `DATABASE_URL=...` | ❌ No | Required |
| Encryption keys | `SECRET_KEY=*** | ❌ No | Required (need `secret()`) |

## Related References

- `references/2026-06-29-template-variable-config-dashboard.md` — Dashboard workflow
- `references/2026-06-29-service-vs-template-variables.md` — Service vars (CLI) vs Template vars (Dashboard)
- `references/2026-06-29-template-variable-repair-pipeline.md` — Repair workflow for mass template fix
