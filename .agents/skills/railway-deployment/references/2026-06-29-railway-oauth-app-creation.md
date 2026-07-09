# Railway OAuth App Creation — Quick Reference

Source: https://docs.railway.com/integrations/oauth/creating-an-app

## Where to Create

**Workspace Settings → Developer → New OAuth App**

Only workspace admins can create/manage apps.

## Two App Types

| Type | Client Secret | PKCE | Auth Method | Use Case |
|------|---------------|------|-------------|----------|
| **Web (Confidential)** | Required | Recommended | `client_secret_basic` / `client_secret_post` | Server-side apps (backends) |
| **Native (Public)** | None | **Required** | `none` (PKCE only) | CLI tools, mobile, desktop, SPAs |

## Required Fields

1. **Name** — User-facing name on consent screen
2. **Redirect URI(s)** — Exact match required (scheme, host, port, path)
   - Dev: `http://localhost:3000/callback`
   - Prod: `https://yourapp.com/callback`
3. **App Type** — Web or Native

## OAuth Endpoints

- **Authorization**: `https://backboard.railway.com/oauth/auth`
- **Token Exchange**: `https://backboard.railway.com/oauth/token`
- **Dynamic Client Registration**: `POST https://backboard.railway.com/oauth/register`

## For CLI Tools (Hermes-style agents)

Use **Native (Public)** type with **PKCE**:

```
Authorization URL:
https://backboard.railway.com/oauth/auth
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=http://localhost:PORT/callback
  &scope=openid
  &code_challenge=CODE_CHALLENGE
  &code_challenge_method=S256

Token Exchange (POST to /oauth/token):
  grant_type=authorization_code
  &code=AUTH_CODE
  &redirect_uri=http://localhost:PORT/callback
  &code_verifier=CODE_VERIFIER
```

**No client secret** sent for Native apps.

## Dynamic Client Registration

For programmatic app creation (e.g., agent bootstrapping):

```
POST https://backboard.railway.com/oauth/register
Content-Type: application/json

{
  "redirect_uris": ["http://localhost:3000/callback"],
  "token_endpoint_auth_method": "none",
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "client_name": "Hermes Agent",
  "scope": "openid"
}
```

Response includes `client_id`, `registration_access_token` (store securely — needed to update/delete the client).

## Key Differences from PAT

| Aspect | PAT (`railway_...`) | OAuth App |
|--------|---------------------|-----------|
| Lifetime | Non-expiring | Access tokens expire; refresh tokens rotate |
| Scope | Account/workspace-wide | User-granted per app |
| Creation | Web UI only (Account Settings) | Web UI or Dynamic Registration API |
| Use Case | CI/CD, agents, automation | Apps acting **on behalf of users** |

## When to Use Each

- **PAT** → Hermes workers, CI pipelines, template publishing, any server-to-server automation
- **OAuth** → User-facing apps where the user logs in and grants permission to act on their Railway account