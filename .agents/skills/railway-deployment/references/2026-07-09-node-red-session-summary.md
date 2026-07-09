# 2026-07-09 node-red Template Session — Summary

**Date:** 2026-07-09
**Template:** `node-red` (code `node-red-2`, published on Railway marketplace)
**Outcome:** Successfully published with EACCES fix baked in. README reverted to use canonical code `node-red-2` (not the random draft code `29hI4C`).

## Lessons Learned

### Lesson 1: EACCES on Railway Volumes (Volume-Ownership vs File-Mode Permissions)

**Symptom** (deploy crashed on first boot):
```
EACCES: permission denied, copyfile '/usr/src/node-red/node_modules/node-red/settings.js' -> '/data/settings.js'
```

**Root cause:**
- Railway volumes mount at the configured path owned by `root:root`
- Base image (`docker.io/nodered/node-red:5.0.0`) runs as the non-root user `node-red` (UID 1000)
- Base image's entrypoint tries to `cp` the default `settings.js` from the upstream image into `/data` (the Railway volume)
- The `node-red` user lacks write permission on the volume root → `EACCES`
- The same volume is also referenced by the healthcheck (`node /healthcheck.js` reads `/data/settings.js`), so the healthcheck would fail even if startup somehow succeeded

**Fix** (verified working 2026-07-09, deployed to marketplace):
```dockerfile
FROM docker.io/nodered/node-red:5.0.0
ENV FLOWS=flows.json \
    NODE_RED_ENABLE_PROJECTS=false \
    NODE_RED_ENABLE_SAFE_MODE=false

# Switch to root so we can chown the volume, then drop privileges
USER root
ENTRYPOINT ["/bin/sh", "-c", "chown -R node-red:node-red /data && exec su node-red -p -c './entrypoint.sh \"$@\"' --"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD node /healthcheck.js
```

**Why each line is needed:**
- `USER root` — the `chown` must run as root
- `chown -R node-red:node-red /data` — fixes volume ownership at runtime (NOT build time — Railway creates the volume at deploy time)
- `exec su node-red -p -c './entrypoint.sh "$@"' --` — runs the upstream entrypoint as the non-root user
- `-p` (preserve environment) — **critical** to keep Railway-injected `$PORT` so the app binds correctly
- The trailing `--` ensures `"$@"` parses correctly even when CMD args are empty (Railway doesn't always pass CMD)

**Generalizability:** This is NOT node-red-specific. Any base image that:
1. Runs as a non-root user by default, AND
2. Writes to a Railway-managed volume at first boot

…will hit the same crash. Common candidates: any image with `USER <uid>` that touches `/data`, `/var/lib/<app>`, `/config`, etc. as the non-root user.

**Pre-Flight Checklist gate (new step 7.5 — proposed):** When adding a volume mount to a template, check the base image's `USER` directive AND the entrypoint script's first-boot write targets. If the user can't write the volume, add the chown-via-`su` pattern.

**Detailed ref:** See `multi-service-railway-config-reference.md` § "Volume Mount Ownership (EACCES at First Boot)".

---

### Lesson 2: `templatePublish` Updates the Existing Published Template, Doesn't Create a New One

**Symptom** (the confusing one):
- Created a new draft with code `29hI4C` via `railway templates create --project <id>`
- Ran `railway templates publish 29hI4C --category ... --description ... --readme-file ... --image ...`
- After publish, the **marketplace URL showed `https://railway.com/deploy/node-red-2`** (NOT `29hI4C`)

**Investigation revealed:**
- The template `node-red-2` was **already in PUBLISHED state** before this session (had been published in a prior session, still listed in the workspace)
- `railway templates delete node-red-2 --yes` (run earlier) failed silently because `templateDelete` cannot remove a PUBLISHED template via API — it's read-only via API per the existing pitfall
- The new drafts (`gFTyNZ`, `spyQkl`, `29hI4C`) were all **drafts** with random 6-char codes
- When `templatePublish` was called on the draft, the **code field is read-only after first publish** (per the existing pitfall), so the existing PUBLISHED template was UPDATED in place with the new Dockerfile/image/description/readme — and the marketplace URL kept its original code `node-red-2`
- The new draft was discarded/ignored in the process

**Net effect (this case, actually GOOD):**
- ✅ The published template kept its human-readable code `node-red-2` (good for SEO and the README)
- ✅ The new Dockerfile (with EACCES fix) was deployed
- ❌ The README had been updated to reference the random draft code `spyQkl` — this was wrong and needed to be reverted to `node-red-2`

**The general rule (now confirmed):**

> **To publish a NEW template with a NEW code, you must FIRST delete or unpublish the OLD published template. Re-publishing always updates the existing one.**

The path to a new code/slug is:
1. `railway templates unpublish <old-code> --yes` (via dashboard, since API is unreliable for unpublish)
2. `railway templates delete <old-id> --yes` (only works after unpublish)
3. `railway templates create --project <id>` (new draft with new random code)
4. Configure variables in dashboard
5. `railway templates publish <new-code> ...`

OR, if you don't care about the code staying the same:
1. Edit the template via the dashboard template editor (reliable for readme/description/image)
2. OR: `railway templates publish <existing-code> --category ... --description ... --readme-file ... --image ...` and accept that the new Dockerfile/vars flow into the existing listing

**Diagnostic: how to know which code is "live" after publish:**
```bash
# Check the marketplace URL
curl -I "https://railway.com/deploy/<code>"   # HTTP 200 = live

# List all templates in the workspace
curl ... -d '{"query":"{ templates(first: 50) { edges { node { code name status } } } }"}'
```

**The misleading-error trap:** The `templatePublish` mutation often returns `"Not Authorized"` or `"Problem processing request"` (per the existing `railway-graphql-misleading-errors-and-verify-discipline.md` ref). The mutation MAY have taken effect despite the error. **Always verify with a separate read query** (the template's `status` should flip to `PUBLISHED` and the code should be findable in the workspace).

**Detailed ref:** See `template-publish-fields-and-restrictions.md` § "Re-Publishing Overwrites the Existing Published Template (No New Code)".

---

## Submodule Hygiene (Unchanged from Earlier Sessions)

- Verified submodule remote before every push: `git config --get remote.origin.url` MUST equal `git@github.com:INAPP-Mobile/railway-node-red.git` (per AGENTS.md rule 7)
- The parent monorepo's `origin-wikijs` was NOT touched — submodule-only operation
- `railway project delete` in non-TTY mode needs an explicit `--project <id>` flag; otherwise, use the GraphQL `projectDelete` mutation directly

## Cross-References

- `multi-service-railway-config-reference.md` § "Volume Mount Ownership (EACCES at First Boot)" — Lesson 1 deep-dive + Dockerfile fix
- `template-publish-fields-and-restrictions.md` § "Re-Publishing Overwrites the Existing Published Template" — Lesson 2 deep-dive + diagnostic flow
- `SKILL.md` § "Pitfall: Base-Image Entrypoint EACCES on Railway Volumes" — top-level entry
- `SKILL.md` § "Pitfall: `templatePublish` Overwrites the Existing Published Template" — top-level entry
- `railway-graphql-misleading-errors-and-verify-discipline.md` — verify-after-mutate discipline (still applies)
- `git-submodule-mistakes.md` — submodule push remote verification
