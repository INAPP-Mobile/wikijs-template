# Railway Session Token Expiration & Re-Auth

**Date:** 2026-06-29
**Problem:** All Railway API calls and CLI commands return `Not Authorized` because the session token expired.

## Symptoms

- GraphQL API returns: `{"errors": [{"message": "Not Authorized", "path": ["projectCreate"]}]}`
- `railway whoami` returns: `Unauthorized. Please check that your RAILWAY_TOKEN is valid`
- `railway` commands fail with interactive login prompts in non-interactive contexts

## Root Cause

The session token stored in `~/.railway/config.json` (`user.accessToken`) has a ~24 hour lifetime. After expiry:
- CLI commands prompt for interactive login (blocking agents)
- Direct API calls with the token return `Not Authorized`
- There is NO programmatic token refresh — OAuth requires browser interaction

## Diagnosis Steps

```bash
# 1. Check if CLI is authorized
railway whoami

# 2. Check if RAILWAY_TOKEN env var is interfering
echo $RAILWAY_TOKEN   # If set, it overrides config.json

# 3. Try unsetting env var
unset RAILWAY_TOKEN
railway whoami         # If this works, the env var was the problem
```

## Fix

The user must re-authenticate:

```bash
# Interactive (opens browser):
railway login

# Headless/SSH (prints URL + code):
railway login --browserless
```

After `railway login` completes, the config.json is updated with a fresh token.

## Distinct Issue: CLI v5.23 Token Field Mismatch

If `railway whoami` fails with "Unauthorized" but you just ran `railway login` successfully, the problem may be that the CLI reads `user.token` while login writes to `user.accessToken`. See `references/2026-06-29-railway-cli-token-field-mismatch.md` for the diagnosis and sync fix.

## Prevention for Agent Contexts

For non-interactive agent sessions, use a persistent **Account Token** (PAT) instead of the session token:

1. Go to https://railway.com/account/tokens
2. Create a token with "No workspace" (account-wide)
3. Set as `RAILWAY_TOKEN` in `~/.hermes/.env`

The PAT doesn't expire and takes precedence over the session token. This prevents the 24-hour expiry from breaking agent workflows.

**Important:** If `RAILWAY_TOKEN` is set in the environment, it overrides `config.json`. If it contains an expired/invalid value, ALL commands fail even after a successful `railway login`. Always check env vars first when debugging auth issues.

## Impact on Template Repair Pipeline

When running a repair pipeline that publishes templates via GraphQL API, ensure:
1. The token is valid BEFORE starting the pipeline (run `railway whoami` first)
2. If the token expires mid-pipeline, the agent cannot recover autonomously — it must ask the user to re-authenticate
3. Consider checking token validity at the start of each pipeline step and failing fast with a clear message if expired
