# Railway CLI Auth Debugging: RAILWAY_TOKEN Env Var Override

**Date:** 2026-06-29
**Symptom:** `railway whoami` returns "Unauthorized" despite `railway login` succeeding
**Root Cause:** `RAILWAY_TOKEN` env var set to placeholder `***` overrides config.json session auth

## Diagnosis

```bash
# Check if RAILWAY_TOKEN is set in env
echo $RAILWAY_TOKEN
# If this prints anything other than empty, it's interfering

# The token in ~/.hermes/.env was set to "***" (placeholder from an earlier
# broken attempt to write the token). This overrides the valid session
# stored in ~/.railway/config.json
```

## The Fix

```bash
# Immediate fix (current session only)
unset RAILWAY_TOKEN
railway whoami  # Should now work

# Permanent fix: remove the broken token from ~/.hermes/.env
sed -i '/^RAILWAY_TOKEN=*** ~/.hermes/.env
```

## How This Happens

1. User/agent writes `RAILWAY_TOKEN=***` to `~/.hermes/.env` (placeholder)
2. Railway CLI reads `RAILWAY_TOKEN` env var **first**, before `~/.railway/config.json`
3. The placeholder `***` is not a valid token → "Unauthorized"
4. Even running `railway login` again doesn't fix it, because the env var takes precedence
5. The `railway login` command appears to succeed (updates config.json) but subsequent commands still fail

## Auth Priority Order

1. `RAILWAY_TOKEN` environment variable (highest priority)
2. `~/.railway/config.json` → `user.accessToken` (session from `railway login`)
3. Interactive login prompt (if both above fail/missing)

## Key Lesson

**Always check env vars first when debugging Railway CLI auth issues.** The most common cause of "Unauthorized" despite being logged in is a stale/invalid `RAILWAY_TOKEN` in the environment.

## Related Config Locations

| Location | Purpose | Format |
|----------|---------|--------|
| `~/.railway/config.json` → `user.accessToken` | Session token from `railway login` | UUID |
| `~/.railway/config.json` → `user.refreshToken` | OAuth refresh token | UUID |
| `~/.railway/config.json` → `user.tokenExpiresAt` | Expiry timestamp | Unix epoch |
| `~/.hermes/.env` → `RAILWAY_TOKEN` | Env var override | `railway_...` or UUID |
| Railway Dashboard → Account Settings → Tokens | Account Token (PAT) | `railway_...` |

## When Each Token Type Works

| Token Type | CLI Commands | GraphQL API | Lifetime |
|------------|-------------|-------------|----------|
| Session token (config.json) | ✅ All | ✅ (with session header) | ~24h |
| Account Token (`railway_...`) | ✅ All | ✅ (with Bearer) | Never |
| Project Token (UUID) | ✅ Deploy only | ✅ (scoped) | Never |
| Expired/invalid token | ❌ "Unauthorized" | ❌ 401 | N/A |
