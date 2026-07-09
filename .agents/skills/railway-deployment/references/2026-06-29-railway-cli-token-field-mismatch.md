# Railway CLI v5.23+ Token Field Name Mismatch

**Date:** 2026-06-29
**Symptom:** `railway whoami` returns "Unauthorized" despite `railway login` succeeding and `user.accessToken` containing a valid token
**Root Cause:** Railway CLI >=5.23 reads `user.token` from config.json, but `railway login` writes to `user.accessToken`

## The Problem

After `railway login` completes successfully, the config.json contains:

```json
{
  "user": {
    "token": null,
    "accessToken": "ZEcLuEuaPPtjdM895-Prh-1E-y3vUnllPp19yWo5hHP",
    "refreshToken": "L5ad6FSKyp8OD4hqTSAj3FzP1FysBd-1iSnYnFgDqEG",
    "tokenExpiresAt": 1782750225
  }
}
```

The CLI reads `user.token` (which is `null`) instead of `user.accessToken` (which has the valid token). This causes ALL CLI commands to fail with "Unauthorized."

## Diagnosis

```bash
# Check the config.json fields
python3 -c "
import json
c = json.load(open('/var/home/ihshim523/.railway/config.json'))
print('user.token:', c['user'].get('token'))
print('user.accessToken:', c['user'].get('accessToken'))
print('user.tokenExpiresAt:', c['user'].get('tokenExpiresAt'))
"

# If token is null but accessToken is set, you have this issue
```

## The Fix

```bash
# One-time fix: copy accessToken to token field
python3 -c "
import json
with open('/var/home/ihshim523/.railway/config.json') as f:
    c = json.load(f)
if not c['user'].get('token') and c['user'].get('accessToken'):
    c['user']['token'] = c['user']['accessToken']
    with open('/var/home/ihshim523/.railway/config.json', 'w') as f:
        json.dump(c, f, indent=2)
print('Fixed: user.token set to user.accessToken')
"
```

## Why This Happens

- Railway CLI v5.22 and earlier read `user.accessToken`
- Railway CLI v5.23+ reads `user.token` (field renamed in the Go backend)
- The `railway login` command still writes to `user.accessToken` (legacy field)
- Result: CLI looks at wrong field → null → "Unauthorized"

## Auto-Sync Pattern for Pipeline Scripts

Add this to the top of any shell script that uses the Railway CLI:

```bash
# Fix: Railway CLI >=5.23 reads user.token but login writes to user.accessToken
python3 -c "
import json
with open('/var/home/ihshim523/.railway/config.json') as f:
    c = json.load(f)
if not c['user'].get('token') and c['user'].get('accessToken'):
    c['user']['token'] = c['user']['accessToken']
    with open('/var/home/ihshim523/.railway/config.json', 'w') as f:
        json.dump(c, f, indent=2)
    print('Synced user.token from user.accessToken')
"
```

## Distinction from Env Var Issue

This is DIFFERENT from the `RAILWAY_TOKEN` env var override problem:
- **Env var issue:** `RAILWAY_TOKEN` is set to an invalid value → overrides everything
- **Field mismatch issue:** `RAILWAY_TOKEN` is NOT set, but CLI reads wrong JSON field → same symptom, different cause

## Token Expiry Check

To verify the token itself is still valid (not just a field issue):

```bash
python3 -c "
import json, datetime
with open('/var/home/ihshim523/.railway/config.json') as f:
    c = json.load(f)
exp = c['user'].get('tokenExpiresAt')
if exp:
    dt = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    print(f'Token expires: {dt}')
    print(f'Current time:  {now}')
    print(f'Expired: {now > dt}')
"
```
