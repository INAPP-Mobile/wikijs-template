# Template Variable Gate Pattern (2026-06-29)

When publishing templates via Kanban pipeline, environment variables must be configured BEFORE publish — Railway CLI cannot do this programmatically. This reference documents the gate + manifest + browser-fallback pattern.

## Problem

- `railway templates create` produces a draft with 0 variables configured
- `railway templates publish` metadata flags (category, description, image, readme) do NOT accept variable config
- GraphQL `templatePublish` / `templateGenerate` have no variable input fields
- End-users see no configuration prompts when deploying templates with 0 vars (confirmed: all 19 INAPP templates had vars=0 on 2026-06-29)
- Reference template: `brody192/filebrowser-template` shows `WEB_USERNAME` as required field with description — this is what proper configuration looks like

## Solution: Draft → Manifest → Gate → Publish

### Draft Agent (Phase 1): Generate Variable Manifest

Parse `.env.example` and save a structured JSON manifest before creating the draft:

```python
# Save to pipeline-logs/template-vars-TEMPLATE_NAME.json
manifest = {
    "template_name": "TEMPLATE_NAME",
    "project_dir": "/home/user/Work/railway/railway-TEMPLATE_NAME",
    "variables": [
        {
            "key": "PORT",
            "default_value": "8080",
            "required": True,
            "description": "Port the service listens on"
        },
        {
            "key": "FB_USERNAME",
            "default_value": "admin",
            "required": True,
            "description": "Username for the admin account (CHANGE AFTER LOGIN)"
        }
        # ... parsed from .env.example
    ],
    "configured": False,
    "editor_url": "https://railway.app/workspace/templates"
}
```

**Description heuristics** (embed in agent body or script):
- `PORT` → "Port the service listens on"
- `*_USERNAME` or `*_USER` → "Username for login/authentication"
- `*_PASSWORD`, `*_PASS`, `*_SECRET` → "Password or secret (CHANGE THIS)"
- `DATABASE*` or `DB_*` → "Database connection string or path"
- `ROOT`, `*_DIR`, `*_PATH` → "File system path"
- `DIALECT` → "Database engine"
- `TZ`, `TIMEZONE` → "Timezone"
- `LOG`, `*_LEVEL` → "Logging level"
- else → "Configuration for {key}"

**Required heuristic**: Any variable containing PORT, USERNAME, PASSWORD, SECRET, DATABASE, URL, ROOT, DIALECT, or CONNECTION should be required=True.

### Publish Agent (Phase 1): Gate Check

Before publishing, verify variables are configured:

```bash
# Check template variable count
railway templates list --workspace INAPP --json | python3 -c "
import json, sys
for t in json.load(sys.stdin):
    if 'TEMPLATE_NAME' in t.get('code',''):
        n = len(t.get('variables',[]))
        print(f'vars={n}')
        if n == 0:
            print('STATUS=UNCONFIGURED')
        else:
            print('STATUS=OK')
            for v in t.get('variables',[]):
                print(f'  - {v.get(\"key\")} required={v.get(\"isRequired\")}')
"
```

**If UNCONFIGURED** — three recovery paths (in order):

#### Path A: Browser tool (preferred for agent autonomy)
```
browser_navigate to https://railway.app/workspace/templates
→ Find draft template → Variables tab
→ For each variable in template-vars-TEMPLATE_NAME.json:
   - Add variable (exact key from manifest)
   - Set default value from manifest
   - Set description from manifest
   - Toggle Required: Yes/No from manifest
→ Save
→ Re-verify with CLI command above
```

#### Path B: Halt and escalate to human
If agent lacks browser tool or browser config fails:
```bash
PUBLISH_ID=$(hermes kankan show "$HERMES_KANBAN_TASK" | grep "children:" | grep -oP 't_[a-f0-9]+' | head -1)
hermes kanban block "$PUBLISH_ID" "CRITICAL: Template variables for TEMPLATE_NAME not configured. Go to https://railway.app/workspace/templates → draft → Variables tab → configure → unblock this card."
```
Then complete task with summary noting block reason.

#### Path C: GraphQL API (future — not available as of 2026-06-29)
Railway GraphQL has no variable mutation. If added, this would be the preferred path.

### Post-Publish Verification

After confirming vars are configured, publish:
```bash
railway templates publish "$TEMPLATE_ID" \
  --category "Other" \
  --description "Deploy TEMPLATE_NAME on Railway" \
  --readme-file README.md \
  --image "https://raw.githubusercontent.com/INAPP-Mobile/railway-TEMPLATE_NAME/main/template-icon.svg" \
  --json
```

## Pipeline Body Integration

### deploy-draft.txt flow
1. Parse `.env.example` → `template-vars-TEMPLATE_NAME.json`
2. `railway templates create --json`
3. Save draft report with TEMPLATE_ID, variable manifest path, editor URL

### deploy-publish.txt flow
1. Read draft report + variable manifest
2. Gate check: verify template shows vars > 0 via `railway templates list`
3. If 0: browser configure → verify again → if still 0: block downstream card
4. If > 0 (or just configured): `railway templates publish`
5. Report: TEMPLATE_CODE + variable count + marketplace URL

## Key Constraint

Template variable configuration is ONLY available through the Railway web dashboard template editor UI. Neither CLI, GraphQL, nor API tokens can set variable required/default/description. The browser tool in Hermes workers is the only programmatic path.
