## Broken Deploy Button URLs — Placeholder and Non-Existent Codes

### Problem

The `INAPP-Mobile/railway-filebrowser` GitHub repo README contained TWO broken deploy button URLs:

1. `https://railway.app/template/xxxxx` — a literal placeholder that was never replaced
2. `https://railway.com/template/mpapKR` — points to a non-existent template code (404)

The correct URL should use the actual published template code: `https://railway.com/deploy?template=filebrowser`

### Root Cause

The repo was created from a template or copy-paste where the deploy button URLs were left as placeholders. No one audited the README after publishing to verify the URLs resolved correctly.

### Impact

- Users clicking "Deploy on Railway" on the GitHub repo get a 404 page
- Lost deployment traffic — users may give up after the broken link
- The template appears unmaintained

### Detection

```bash
# Extract deploy button URLs from README
grep -oP 'railway\.(app|com)/(deploy\?template=|template/)[^\s")]+' README.md

# Verify each URL resolves
curl -sI "https://railway.com/deploy?template=<code>" | head -1
# HTTP 200 = valid, HTTP 404 = broken
```

### Fix

1. Get the actual published code: `railway templates list --json | python3 -c "import json,sys; [print(t['code']) for t in json.load(sys.stdin) if t['name']=='filebrowser']"`
2. Update README: replace all broken URLs with `https://railway.com/deploy?template=<actual-code>`
3. Push to GitHub
4. Optionally re-publish via GraphQL `templatePublish` to sync the README to the marketplace

### Prevention Checklist

After publishing any template, verify ALL of these in the README:
- [ ] Deploy button URL uses the **actual published code** (not the desired slug)
- [ ] No placeholder strings like `xxxxx`, `YOUR_CODE_HERE`, `TEMPLATE_CODE`
- [ ] No references to other template codes (copy-paste from other repos)
- [ ] URL returns HTTP 200: `curl -sI "https://railway.com/deploy?template=<code>" | grep HTTP`
