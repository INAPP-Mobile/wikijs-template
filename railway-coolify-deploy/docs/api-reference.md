# Coolify v4 API Reference — Endpoints We Actually Use

> **Source of truth:** https://coolify.io/docs/api — checked at write time.
> If Coolify V4's payload shape changes between minor releases, the snippet
> below is what `register-services.sh` posts.
>
> **Auth:** `Authorization: Bearer <token>` minted from
> `Coolify UI → Settings → API Tokens → Create`.
>
> **Base URL example:** `https://coolify.example.com/api/v1`

## 1. Create project (once)

```http
POST /projects
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "INAPP Railway Templates",
  "description": "Self-hosted gallery of 6 INAPP Railway templates deployed via Coolify"
}
```

Response:
```json
{ "uuid": "abc123..." }
```

We store this UUID and reuse it for every application create.

## 2. List servers (so we know the droplet UUID)

```http
GET /servers
Authorization: Bearer <token>
```

Coolify tracks each "remote" (Docker host) you onboard. We installed Coolify
on the droplet itself, so it's both controller and worker.

Response shape:
```json
[
  { "uuid": "s_def...", "name": "coolify-gallery", "ip": "..."
   , "is_reachable": true, "is_usable": true }
]
```

We pick the one matching `COOLIFY_DROPLET_NAME` from `.env`.

## 3. Create an application (per service)

```http
POST /projects/{project_uuid}/applications/applications
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "gotify",
  "description": "Self-hosted push notification server",
  "git_repository": "https://github.com/INAPP-Mobile/railway-gotify",
  "git_branch": "main",
  "build_pack": "dockerfile",
  "server_id": "s_def...",

  "ports_exposes": "8080",
  "health_check_path": "/health",
  "health_check_port": "8080",
  "health_check_method": "GET",
  "health_check_interval": 30,
  "health_check_timeout": 5,
  "health_check_retries": 3,
  "health_check_start_period": 30,

  "fqdn": "gotify.example.com",

  "envs": [
    {"key": "GOTIFY_SERVER_PORT", "value": "8080", "is_multiline": false, "is_secret": false},
    {"key": "GOTIFY_DEFAULTUSER_NAME", "value": "admin", "is_multiline": false, "is_secret": false}
  ]
}
```

Notes:
- `fqdn` is the **public** FQDN that Traefik will route to this container.
  Coolify auto-provisions Let's Encrypt SSL for it.
- `server_id` is the **droplet** UUID (Coolify calls its workers `servers`).
- Do **NOT** include `instant_deploy` — it was renamed/removed in some
  Coolify v4.x betas and 422s the request in stable. The companion POST
  `/applications/{uuid}/deploy` call handles initial deployment.
- The `envs` array MUST contain exactly `is_multiline` + `is_secret`. Do
  **NOT** add `is_literal` — it appeared briefly in some 4.0 betas and
  422s the request in v4.0.0 stable.

## 4. Queue a deploy

```http
POST /applications/{app_uuid}/deploy
Authorization: Bearer <token>
Content-Type: application/json

{ "tag": "initial" }    # run a fresh build+deploy
```

## 5. Per-app storage (volumes)

Currently **not in the application-create payload** — Coolify requires a
follow-up PATCH or the UI to attach volumes. For now, register-services.sh
prints a warning per service reminding the operator to attach the
recommended mount path via the UI.

UI path: `Project → Service → Storage → Add Persistent Storage`

For our maps:
- Gotify:  `/app/data`         → volume `gotify-data`
- Memos:   `/var/opt/memos`    → volume `memos-data`
- Kanboard:`/var/www/app/data` → volume `kanboard-data`
- Netdata: `/host`             → bind-mount `/`
- Stirling:`/configs`          → volume `stirling-configs`
- Node-RED:`/data`             → volume `nodered-data`

These will be wired into `register-services.sh` once we verify the
PATCH endpoint that attaches a volume to an existing application.

## 6. Read-side endpoints (used by verify.sh)

`verify.sh` does **not** call the API — it just hits each service's public
URL via Traefik. If you want to inline the API call:

```bash
curl -sS "${COOLIFY_BASE_URL}/applications/<uuid>" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
  | jq '.status, .last_restart_at, .deployment_url'
```

## 7. Common errors at the time of writing

| HTTP | Body | Cause | Fix |
|---|---|---|---|
| 401 | "Unauthenticated" | Token missing/expired | Re-mint in UI |
| 422 | "The git repository must be a valid URL" | Typo in REPO url | Spellcheck |
| 422 | "The domain field is required" | Forgot `fqdn` | Add `fqdn` |
| 422 | "The fqdn has already been taken" | Domain used by another service | Unique subdomain per app |
| 500 | — | Coolify internal error | Check `cd /data/coolify && docker compose logs coolify` |

## 8. Verifying your version

```bash
# From the Coolify UI → Settings → Instance
# Coolify shows:  "Coolify v4.0.0"
```

Coolify's API may have minor payload differences between `4.0.0` and patched
versions. If `register-services.sh` returns a 422 with a body mentioning a
field we didn't set, check Coolify's CHANGELOG and compare the
`POST /projects/.../applications/applications` schema in their OpenAPI.
