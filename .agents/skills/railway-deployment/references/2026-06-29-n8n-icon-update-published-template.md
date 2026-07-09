# N8n Icon Update on Published Template — 2026-06-29

## Problem

The published template `railway-n8n` showed the generic Railway placeholder icon instead of the n8n logo, despite `template-icon.svg` existing in the repo root.

## Root Cause

The template was originally published without the `--image` flag. The `image` field was `null` in the marketplace. Railway does NOT auto-detect `template-icon.svg` from the repo — it must be explicitly set at publish/update time.

## Diagnosis

```bash
# Check current image field via GraphQL
python3 -c "
import json, os, urllib.request
tok = open(os.path.expanduser('~/.railway/api-token')).read().strip()
req = urllib.request.Request(
    'https://backboard.railway.com/graphql/v2',
    data=json.dumps({'query': '{ template(code: \"railway-n8n\") { id code name image } }'}).encode(),
    headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json', 'User-Agent': 'railway-cli/5.23.1'}
)
with urllib.request.urlopen(req) as resp:
    print(json.dumps(json.loads(resp.read()), indent=2))
"
# Result: "image": null
```

## Fix

```bash
# Update only the image on a published template
unset RAILWAY_TOKEN  # Force CLI to use valid session from config.json
railway templates publish railway-n8n \
  --image "https://raw.githubusercontent.com/INAPP-Mobile/railway-n8n/main/template-icon.svg" \
  --json
```

The command accepts partial `TemplatePublishInput` — you only need to pass the fields you want to change. Omitted fields (category, description, readme) are preserved from the existing template.

## Auth Pitfall

The `RAILWAY_TOKEN` env var was stale (different from the session token in `~/.railway/config.json`). This caused "Unauthorized" on every CLI command. Fix: `unset RAILWAY_TOKEN` to force the CLI to use the valid session token from `~/.railway/config.json`.

## Verification

After update, the JSON output shows:
```json
{
  "image": "https://raw.githubusercontent.com/INAPP-Mobile/railway-n8n/main/template-icon.svg",
  "status": "PUBLISHED"
}
```

The marketplace card refreshes within minutes (CDN cache).
