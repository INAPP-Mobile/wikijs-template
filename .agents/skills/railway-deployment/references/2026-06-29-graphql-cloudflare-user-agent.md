# GraphQL Cloudflare User-Agent Requirement (2026-06-29)

## Problem

Railway's GraphQL API (`https://backboard.railway.com/graphql/v2`) returns HTTP 403 with error code `1010` when called from Python's `urllib.request` — even with a valid auth token.

Error body: `error code: 1010`

This is a Cloudflare challenge, NOT a Railway authentication error.

## Root Cause

Cloudflare's bot detection rejects requests that lack a `User-Agent` header. Python's `urllib.request` does not set a User-Agent by default. `curl` works because it sends `User-Agent: curl/X.Y.Z`.

## Fix

Always include a `User-Agent` header in GraphQL requests:

```python
req = urllib.request.Request(
    endpoint,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent": "railway-cli/5.23.1",  # Any realistic UA works
    },
)
```

## Verification

```python
# FAILS (403 error 1010):
req = urllib.request.Request(url, data=payload, headers={
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
})

# WORKS:
req = urllib.request.Request(url, data=payload, headers={
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "User-Agent": "railway-cli/5.23.1",
})
```

## Affected Patterns

- `urllib.request.urlopen()` in Python
- `httplib` / `http.client` in Python
- Any HTTP client that doesn't set User-Agent by default

## NOT Affected

- `curl` (sets UA automatically)
- `requests` library with default UA (`python-requests/X.Y.Z`)
- `httpx` with default UA
