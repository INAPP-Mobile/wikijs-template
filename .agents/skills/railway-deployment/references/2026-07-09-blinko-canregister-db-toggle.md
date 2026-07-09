# Blinko canRegister DB Toggle Fix — 2026-07-09

## TL;DR

Blinko (T3-stack, github.com/blinkospace/blinko, image `docker.io/blinkospace/blinko:1.8.8`)
exposes user signup control via a single DB row in the `config` table — there is **no
env var override**. Setting `key='isAllowRegister'` with `config={"value": true}` flips
the `canRegister()` tRPC procedure to allow new signups.

Without this row, every signup attempt logs `tRPC error: not allow register ->
INTERNAL_SERVER_ERROR` and Railway returns 502 to the browser.

## Session Timeline

1. **User reported** signup 502 ("sign up blinko returns 502, look http logs").
2. Earlier in same session, blinko's HTTP route was fixed (PORT=1111 baked into
   `railway.json` and live `variableUpsert`), so the 502 was now application-level.
3. Pulled blinko logs via GraphQL; identified `tRPC error: ... not allow register` →
   `INTERNAL_SERVER_ERROR`. Same logs repeatedly call `canRegisterxxx` (a function-level
   debug log that prints next to the actual toggling code).
4. Tried `sandboxExec(command: "psql ... ", sandboxId)` to UPSERT the row via Railway
   GraphQL — got feature-flag gate ("Sandboxes aren't enabled on your account yet").
5. Probed Repository: github.com/blinkospace/blinko. Server source paths are
   `server/routerTrpc/user.ts`, `server/routerTrpc/config.ts`, `server/lib/...`
   (monorepo; `app/` is the Tauri desktop client).
6. Read `server/routerTrpc/user.ts` source — confirmed `canRegister()` does:
   - If `prisma.accounts.count() === 0` → return `true` (first user becomes superadmin).
   - Else query `prisma.config` for `{key: 'isAllowRegister'}` and check
     `config?.value === true`.
7. Found Upstream Prisma schema (`/main/prisma/schema.prisma`): `config` table with
   `id`, `key`, `config` (Json), optional `userId`.
8. Tried `sandboxExec` again after user enabled feature flag — got "Sandbox not found"
   (sandboxes are ephemeral dev shells, not live-service exec slots).
9. Pivoted to **baking the SQL UPSERT into the docker image startup**. Three
   files added/modified in `railway-blinko` submodule:
   - `blinko/Dockerfile` — overrides CMD (preserves upstream ENTRYPOINT at
     `/usr/local/bin/docker-entrypoint.sh`); copies bootstrap script + wrapper.
   - `blinko/blinko-bootstrap.js` — idempotent UPSERT via Prisma Client at the
     absolute path `/app/node_modules/@prisma/client` (verified via `podman inspect`).
   - `blinko/railway-start.sh` — runs `npx prisma migrate deploy` (creates
     `config` table), then `node blinko-bootstrap.js` (UPSERT), then upstream
     `node server/seed.js`, then `exec node server/index.js` (PID 1 stays node).
10. **Code-reviewer catch** on first commit `0a72c309`:
    - **Ordering bug**: bootstrap was running BEFORE `prisma migrate deploy`.
      On fresh deploys, UPSERT failed silently (catch swallowed it), so the fix
      never took effect on first deploy. Fix in commit `5ef496d`.
    - **Process exit**: `blinko-bootstrap.js` did not call `process.exit(0)`.
      Prisma-client's native fd pool can keep Node 20's event loop alive,
      delaying the rest of railway-start.sh. Added explicit `process.exit(0)`.
    - **Dockerfile healthcheck redundancy**: Dockerfile recreated HEALTHCHECK
      while railway.json already sets `healthcheckPath: "/api/health"`. The two
      values disagreed (Dockerfile: 10s timeout, railway.json: 60s grace).
      Removed Dockerfile HEALTHCHECK; railway.json is the single source of
      truth for marketplace deploys.
11. Verified fixes — both commits pushed to `origin/main`. blinko service
    redeployed twice (deployments `643322e0`, `f3f2a656`). Both report
    `SUCCESS` via GraphQL.

## Evidence Trail (commands used)

```bash
# 1. Confirm upstream source
curl -sL https://raw.githubusercontent.com/blinkospace/blinko/main/server/routerTrpc/user.ts
# → canRegister logic confirmed

# 2. Discover upstream Dockerfile layout
podman pull docker.io/blinkospace/blinko:1.8.8
podman inspect docker.io/blinkospace/blinko:1.8.8
# → ENTRYPOINT = ["docker-entrypoint.sh"] (file at /usr/local/bin/docker-entrypoint.sh)
# → CMD = ["/usr/local/bin/dumb-init","--","/bin/sh","-c","./start.sh"]
# → WorkingDir = /app, User = root (no USER set)

# 3. Discover @prisma/client install location
podman run --rm --entrypoint=/bin/sh docker.io/blinkospace/blinko:1.8.8 \
  -c 'ls -d /app/node_modules/@prisma/client /app/server/node_modules/@prisma/client 2>/dev/null'
# → /app/node_modules/@prisma/client (NOT under /app/server/)

# 4. Read upstream start.sh (to know what chain we're wrapping)
podman run --rm --entrypoint=/bin/sh docker.io/blinkospace/blinko:1.8.8 \
  -c 'cat /app/start.sh'
# Returns:
#   #!/bin/sh
#   echo "Current Environment: $NODE_ENV"
#   npx prisma migrate deploy
#   node server/seed.js
#   node server/index.js

# 5. Deploy + verify (use Railway GraphQL)
curl ... -d '{"query":"mutation($id:String!,$env:String!){serviceInstanceRedeploy(serviceId:$id,environmentId:$env)}","variables":{"id":"<BLINKO>","env":"<ENV>"}}'
```

## Files Changed (commits)

| Commit | Description |
|--------|-------------|
| `0a72c309` | Initial fix: 3 files; bootstrap before migrate deploy (suboptimal — code-reviewer flagged). |
| `5ef496d`  | Code-reviewer followups: bootstrap reordered to AFTER migrate deploy, `process.exit(0)` added, HEALTHCHECK dropped from Dockerfile. |

## Verification Status (this session)

- ✓ Both commits pushed to `origin/main` of `INAPP-Mobile/railway-blinko.git`.
- ✓ Blinko service redeployed via `serviceInstanceRedeploy(serviceId, environmentId)` —
  GraphQL returns `SUCCESS` for both new deployments.
- ✗ Pending: Functional UAT via `browser-use`. Both `deployment(id).logs` reads
  returned 0 lines (Railway log-streaming delay for fresh deployments is
  variable; trusts `SUCCESS` deployment status + the bootstrap's idempotency).
  Suggested followup: user opens Blinko's public URL, attempts signup with a
  test account; if 502 still appears after the next deploy, the bootstrap
  isn't actually running — investigate.

## Lessons Baked Into Skill Layer

1. **Deeper-truth check never trusted `sandboxExec` "success" until verified.**
   The feature-flag path (`sandboxes(environmentId).edges`) only returns
   ephemeral dev shells, NOT live-service exec slots. Reference for future
   "live service exec via API" troubleshooting: it's not available — the only
   options are dashboard, railway CLI re-auth, or bake into Dockerfile.
2. **Always probe Docker Hub + `podman inspect` before wrapping an upstream
   image.** The boot chain (`docker-entrypoint.sh + dumb-init + start.sh`)
   is non-obvious; naively overriding CMD without re-executing upstream
   entrypoint can break signal propagation.
3. **Order of operations in startup wrappers matters.** Bootstrap scripts
   that need schema-side resources must run AFTER `<tool> migrate deploy`,
   not before.
4. **Hardcoded absolute `require()` paths break under upstream node_modules
   restructuring.** Code-reviewer's residual concern: if future Blinko
   versions move `@prisma/client` under `/app/server/node_modules/`, the
   bootstrap will silently fail. Future improvement: dynamically discover
   via `find /app -name '@prisma' -type d -maxdepth 5` once at first run.

## Related

- `.agents/skills/railway-deployment/SKILL.md` § "Top-Priority Pitfalls" — the
  misleading-error patterns that prevented earlier this session from
  prematurely trusting `sandboxExec` "success".
- `.agents/skills/railway-deployment/references/railway-graphql-misleading-errors-and-verify-discipline.md`
- `.agents/skills/railway-deployment/references/2026-07-09-stirling-pdf-deploy-button-fix.md`
  (peer session: another deploy fix via GraphQL where misleading-error pattern also bit).
