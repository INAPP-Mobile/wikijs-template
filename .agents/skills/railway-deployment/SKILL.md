---
name: railway-deployment
description: Deploy projects Railway, manage services, publish templates marketplace. Covers template design rules, two-variable-file system, pre-publish validation, volume binding, Python-driven pipeline automation with small LLM phases, Config-as-Code single-service limitation vs Infrastructure as Code (IaC) multi-service workflow.
tags: [railway, deployment, cli, template, devops, pipeline]
---

# Railway Template Design

Deploy projects, publish templates Railway marketplace. Covers the full lifecycle: scaffold, validate, build, deploy, troubleshoot, publish.

## ⚠️ Core Agent Constraints (see AGENTS.md for source of truth)

These are the **highest-priority rules** in this project. Violating them wastes hours of work and produces broken marketplace templates. Read them before any template work:

- **Rule 1 — No text in icons.** Template icons must be **graphical only** — no `<text>`, no `<tspan>`, no rendered words. Match the existing icon style (e.g., `800×800` viewBox, `rx=120` rounded square, brand-aligned gradient).
- **Rule 2 — Sentence case display name.** `"Plausible CE"`, not `"plausible-ce"`. Use sentence case unless the upstream project name itself is lower case.
- **Rule 3 — Do NOT auto-publish.** Keep templates on **DRAFT** until issues are fully fixed. Publishing is irreversible via the API (`templateUnpublish` returns a misleading 500 wrapper — see `railway-graphql-misleading-errors-and-verify-discipline.md`).

When in doubt, defer to `AGENTS.md` and ask the user.

## ⚠️ Pre-Flight Checklist (12 steps — run BEFORE any template work)

**This is the gate that prevents the trial-and-error patterns from past sessions (URL ordering crashes, raw-image sibling macro issues, 2-boot deadlocks, plugin-var leakage, lost+found PGDATA traps, duplicated template names, submodule push clobber, etc.).** Run the 12 steps in order; each has a "what to do" + "what to check" + "common gotcha" in `references/pre-flight-checklist.md`.

**Project rules (1-2):**
1. **AGENTS.md project rules** — icon = graphical-only, name = sentence case, template on DRAFT (not PUBLISHED), submodule remote verified
2. **Auth + token health** — `unset RAILWAY_TOKEN && railway whoami` succeeds

**Technical gates (3-9):**
3. **TOML syntax** — `python3 -c "import tomllib; tomllib.load(open('railway.toml','rb'))"` (if `railway.toml` exists)
4. **Upstream image inspection** — pull image, read entrypoint/CMD, find app dir with `podman run --rm ...`
5. **Macro resolution plan** — list every `${{...}}` your template needs, map to the matrix (in `template-deploy-pitfalls.md`)
6. **Init-time self-references** — does the app boot-call a local API that needs DB records? If yes → preconfig + 2-boot pattern
7. **Volume mount geometry** — for raw Postgres/MySQL siblings, use parent-mount convention (NOT `/var/lib/postgresql/data`)
8. **Two-file sync** — `template-vars.json` and `template-editor-raw.json` have identical keys
9. **No plugin-var leakage** — `${{Postgres.DATABASE_URL}}` etc. are NOT in form files (Railway auto-injects)

**Dedup + lifecycle (10-12):**
10. **Dedup check** — does the template code already exist on Railway? (substring match in BOTH directions)
11. **Clean slate before `templates create`** — no manual var overrides captured
12. **Test deploy + final verification** — `railway up` + poll HTTP 200 + verify env vars resolved

**For full commands, verification per step, and common gotchas: [`references/pre-flight-checklist.md`](references/pre-flight-checklist.md)**

## Reference Files

For deep-dive context, see `references/`:

- `references/stale-credentials-plugin-rotation.md` — why `${{Postgres.DATABASE_URL}}` goes empty, why password auto-rotation breaks deploys, why duplicate same-type services confuse macros
- `references/postgres-component-vars-vs-database-url.md` — when use individual `POSTGRES_USER`/`POSTGRES_PASSWORD`/`RAILWAY_PRIVATE_DOMAIN`/`POSTGRES_DB` vars single `${{Postgres.DATABASE_URL}}`
- `references/plausible-crash-malformed-cmd.md` — v3.2.1 entrypoint.sh subcommands versus error-soup CMD strings, `BASE_URL` required, PGDATA path gotcha
- `references/base-url-required-checklist.md` — apps require non-empty public URL var boot use `${{RAILWAY_PUBLIC_DOMAIN}}`
- `references/end-to-end-template-workflow.md` — 10-phase publish-fix-verify cycle, duplicate service detection, hardcoded credential audit, companion-mapping wiring
- `references/per-service-form-structure.md` — per-service file layout and what gets a form
- `references/plugin-vars-vs-form-vars.md` — plugin auto-injected vars never go in deploy form
- `references/template-form-ux-and-workflow.md` — draft/publish/unpublish flow, empty-form UX bug, original-project-as-test-bed, `&&` display rendering bug
- `references/first-step-toml-syntax-diagnostics.md` — **FIRST check when builds fail**: `key "value"` vs `key = "value"` silently kills all builds
- `references/templates-create-requires-image-source.md` — `railway templates create` CLI needs source; GitHub repo connect workaround enables CLI dashboard-free draft creation. **CLI-created templates have EMPTY variables** — must configure via dashboard editor.
- `references/config-as-code-vs-iac.md` — **Config as Code (`railway.toml`/`railway.json`) only supports ONE service.** Multi-service projects with plugins REQUIRE Infrastructure as Code (`.railway/railway.ts`).
- `references/healthcheck-path-override-limitation.md` — root-level `healthcheckPath` propagates to all services, `railway.toml` SINGLE-service conflict (leaks `/api/health` to multi-service), empty-string `""` STILL auto-detects, `serviceInstanceUpdate` does NOT persist across redeploys, framework auto-detection behavior, `serviceCreate` missing plugin env vars, variable override via `railway deploy -v KEY=VALUE`. **REQUIRED READING before any multi-service template work.**
- `references/multi-service-railway-config-reference.md` — verified working directory structure, file contents, volume mounts, variable injection table, entrypoint inspection procedure, filesystem permission pitfalls
- `references/plausible-ce-and-postgres-docker-patterns.md` — **Plausible v3.2.1 entrypoint.sh subcommands** (`db migrate` + `run`), Railway Postgres-SSL image requirements (volume mount + POSTGRES_PASSWORD + no PGDATA), env var reference tables.
- `references/fix-broken-repo-template-workflow.md` — **fix broken repo → deploy → GitHub source → create draft** end-to-end workflow (Plausible fix pattern)
- `references/railway-graphql-template-introspection.md` — inspect AND build templates via GraphQL API: full multi-service build recipe, mutation reference, serializedConfig format, literal-value-stripping gotcha
- `references/cli-deploy-missing-template-vars.md` — `railway up` does NOT inject template vars; app crashes without BASE_URL/SECRET_KEY_BASE
- `references/railway-graphql-misleading-errors-and-verify-discipline.md` — **2026-07-08 lesson:** `templatePublish`/`templateUnpublish`/`projectDelete` return misleading `"Not Authorized"` or `"Problem processing request"` errors. The mutation may or may not have taken effect — ALWAYS verify with a separate read query. Includes which mutations are flaky vs which genuinely fail, and the verify-after-mutate discipline.
- `references/railway-template-publish-workflow.md` — **2026-07-09 reference (NEW):** canonical end-to-end path from "no working template" → PUBLISHED marketplace listing. Stitched together from the existing gotcha references + the 2026-07-09 blinko session's NEW findings: the CLI auth boundary (Bearer works for queries; only `unset RAILWAY_TOKEN` + interactive shell works for writes); the `--readme-file <path>` requirement on `railway templates publish`; the `railway service source connect --image postgres:16-alpine --service <id>` CLI attach for plugin-managed services without changing volume mounts; the AGENTS.md-rule-3-vs-user-override dance.
- `references/template-publish-fields-and-restrictions.md` — **2026-07-08 lesson:** Field-level constraints for `templatePublish` (75-char description limit, valid category enum, image URL must serve raw SVG/PNG, no `simpleicons.org` HTML). Plus: already-published templates are read-only via API — use dashboard template editor for readme/description/image updates. **2026-07-09 addendum:** Re-publishing a new draft actually UPDATES the existing published template in place (the `code` field is read-only after first publish) — to get a new code, you must unpublish + delete the old one first.
- `references/2026-07-09-node-red-session-summary.md` — **2026-07-09 lessons:** (1) EACCES on Railway volumes when base image runs as non-root and writes to /data — fix with `USER root` + `chown` + `su -p` ENTRYPOINT. (2) `templatePublish` overwrites the existing published template rather than publishing a new draft — the original human-readable code is preserved. Full case study with diagnostic flow.
- `references/multi-service-railway-config-reference.md` — verified working directory structure, file contents, volume mounts, variable injection table, entrypoint inspection procedure, filesystem permission pitfalls. **2026-07-09 addendum:** new "Volume Mount Ownership (EACCES at First Boot)" section — base images running as non-root that write to a volume on first boot need `USER root` + chown + `su` ENTRYPOINT fix.
- `references/dashboard-publish-form-template.md` — **2026-07-09 lesson:** Exact structure of the dashboard's manual-publish form, validator section requirements (`# Deploy and Host`, `## About Hosting`, `## Common Use Cases`, `## Dependencies`, `## Why Deploy` — all with **lowercase appname** in headings, even though `AGENTS.md` rule 2 says sentence case for display names), required boilerplate for the "Why Deploy" section, and the workspace-level publish-block diagnostic + resolution path (file a ticket at <https://station.railway.com>, NOT `team@railway.app` — Railway explicitly does not handle this kind of issue over email; auto-responses from team@ redirect all general inquiries to station.railway.com).
- `references/git-submodule-mistakes.md` — **2026-07-08 lesson:** Submodule vs parent commit separation. Wrong-remote push recovery via `git push --force-with-lease <remote> <previous-tip>:<branch>` (NOT `--force`). Submodule's own remote is unaffected by parent push mistakes.

## ⚠️ Top-Priority Pitfalls (2026-07-08 Lessons)

These are the most important pitfalls to internalize. Read these before any template publish or submodule push.

### Pitfall: API Errors Are Misleading — Always Verify With a Separate Query

Railway's GraphQL API wraps many real errors (auth, scope, validation, internal server error) inside one of two misleading response shapes:

- `"Not Authorized"` (no `errorExtensions.code`) — HTTP 500 INTERNAL_SERVER_ERROR
- `"Problem processing request"` — HTTP 500 INTERNAL_SERVER_ERROR

**You cannot tell from the error message which one happened.** The mutation may have succeeded, partially succeeded, or genuinely failed.

**Affected mutations (verified 2026-07-08):**

| Mutation | Symptom | Real outcome |
|----------|---------|--------------|
| `templatePublish` (first call) | `"Not Authorized"` 500 | **Mutation took effect** despite the error |
| `templatePublish` (re-publish) | `"Not Authorized"` or `"Problem processing request"` | **Flaky.** Some fields update, others don't. |
| `templateUnpublish` | `"Not Authorized"` 500 | Genuine failure. State remained PUBLISHED. |
| `projectDelete` (production) | `"Not Authorized"` 500 | Genuine failure. Project verifiably still present. |
| `variableUpsert` | `"Problem processing request"` 500 | Often does not take effect. Use `railway variable set` CLI. |

**Fix:** After every mutation, immediately run a separate read query and compare state:

```bash
# 1. Run mutation
curl ... -d '{"query":"mutation { templatePublish(...) {...} }", ...}'

# 2. ALWAYS run a separate read query (don't trust the mutation response)
curl ... -d '{"query":"query($id: String!) { template(id: $id) { code status description image readme } }", "variables":{"id":"<TEMPLATE_ID>"}}'
```

**Give up on the API for:** readme/description/image updates on already-published templates (use dashboard), unpublish (use dashboard), delete production project (use dashboard). See `references/railway-graphql-misleading-errors-and-verify-discipline.md` for the full debugging flow.

### Pitfall: Already-Published Templates Are Read-Only Via API

After a template is in `PUBLISHED` state, calling `templatePublish` again to update fields is **unreliable**:

| Field | Update on re-publish? |
|-------|----------------------|
| `category` | Usually works |
| `image` | Sometimes works (worked on 2nd attempt) |
| `description` | Inconsistent (worked once, failed silently once) |
| `readme` | **Often silently rejected.** Set to `null` or unchanged. |

**The only reliable path is the dashboard template editor:**
```
https://railway.com/workspace/templates/<template-id>
```

The dashboard's UI gives clearer error messages per field and persists readme/description/image reliably. The API is fine for the **first** publish; for **updates**, use the dashboard. See `references/template-publish-fields-and-restrictions.md` for the full field constraints (75-char description, valid category enum, image URL rules, etc.).

### Pitfall: Submodule Pushes Require Remote Verification

This project is a **collection of git submodules** (`railway-plausible/`, `railway-n8n/`, `railway-open-webui/`, etc.) under a parent repo. The parent repo's `master` branch contains gitlink pointers.

**Mistake pattern:** Pushing a parent commit to a remote that was configured for a *different* submodule (e.g., pushing a parent commit to `origin-wikijs` which points to `wikijs-template.git` when the change only updated a different submodule's gitlink).

**Consequence:** A wrong-remote push can be cleanly reverted with `git push --force-with-lease` (NOT `--force`) without touching the submodule's own remote:

```bash
# 1. Capture the previous tip BEFORE doing anything else
git rev-parse origin-wikijs/master   # save this SHA

# 2. Revert the wrong push
git push --force-with-lease origin-wikijs <PREVIOUS_TIP>:master
```

`--force-with-lease` fails safely if someone else pushed in the meantime. `--force` clobbers concurrent work. The submodule's own remote is unaffected by the wrong parent push. See `references/git-submodule-mistakes.md` for the full recovery flow.

## Pitfall: Base-Image Entrypoint EACCES on Railway Volumes (2026-07-09)

**Symptom** (deploy crashes immediately, no build error):
```
EACCES: permission denied, copyfile '/usr/src/<app>/settings.js' -> '/data/settings.js'
```

**Root cause:** Railway-managed volumes mount at the configured path owned by `root:root`. Many base images (`nodered/node-red`, `linuxserver/*`, `nginx-unprivileged`, etc.) run as a non-root user (UID 1000) by default and try to write to the volume on first boot (copying default config, creating a database, writing settings). The non-root user lacks write permission on the volume root → `EACCES` → the app never starts.

**Fix** (verified working 2026-07-09, deployed to marketplace as `node-red` template):
```dockerfile
USER root
ENTRYPOINT ["/bin/sh", "-c", "chown -R <upstream-user>:<upstream-group> /<volume-path> && exec su <upstream-user> -p -c './entrypoint.sh \"$@\"' --"]
```

**Why each part is needed:**
- `USER root` — the `chown` requires root
- `chown -R <user>:<group> /<path>` — fix ownership at **runtime** (Railway creates the volume at deploy time, not build time)
- `exec su <user> -p -c '...'` — drop back to non-root for the actual app
- `-p` (preserve env) — **critical** to keep Railway-injected `$PORT`

**Generalizable:** Any base image that (a) runs as non-root AND (b) writes to a volume on first boot will hit this. Diagnostic: `podman run --rm --entrypoint /bin/sh <image> -c "cat /entrypoint.sh" | grep -E 'cp |touch |>> '` then check if the write target is a volume mount.

See `references/multi-service-railway-config-reference.md` § "Volume Mount Ownership (EACCES at First Boot)" for the full fix + alternative patterns.

## Pitfall: `templatePublish` Overwrites the Existing Published Template (2026-07-09)

**Symptom:** You create a fresh draft, run `railway templates publish <new-draft-code> --category ...`, and the marketplace URL still shows `https://railway.com/deploy/<old-code>`, not your new draft code. The new draft disappears.

**Root cause:** `templatePublish` does NOT create a new marketplace listing. It **updates the existing published template in place**, and the `code` field is **read-only after first publish**. If a template with your project's name is already PUBLISHED in the workspace, your publish call updates that one (keeping the original code) and discards your new draft.

**To get a NEW code, you must FIRST unpublish + delete the old template:**
1. Unpublish via dashboard (API is unreliable): `https://railway.com/workspace/templates/<id>` → ⋮ → Unpublish
2. Delete: `railway templates delete <id> --yes`
3. Create fresh draft: `railway templates create --project <id> --json`
4. Configure variables in dashboard
5. Publish: `railway templates publish <new-code> ...`

**The good case:** If you don't care about the code changing, the new Dockerfile + vars flow into the existing listing — the human-readable code in your README's "Deploy on Railway" button stays valid.

**Misleading-error trap:** `templatePublish` often returns `"Not Authorized"` despite the mutation taking effect (per `railway-graphql-misleading-errors-and-verify-discipline.md`). Always verify with `curl -I https://railway.com/deploy/<code>` (HTTP 200 = live).

See `references/template-publish-fields-and-restrictions.md` § "Re-Publishing Overwrites the Existing Published Template" for the full diagnostic flow.

## Pitfall: `railway.toml` Leaks `healthcheckPath` to ALL Services

If your repo has a `railway.toml` with a `[deploy]` block, Railway parses it as single-service Config-as-Code. The `healthcheckPath` from that block is applied to the first service parsed — and since single-service config doesn't support `[[services]]` arrays properly, ClickHouse and other companions ALSO get the root service's healthcheck path.

**Symptom**: ClickHouse gets `healthcheckPath: /api/health` even though the template's serializedConfig specifies `/ping`.

**Fix**: Remove `railway.toml` entirely for multi-service templates. Use `.railway/railway.ts` IaC or the GraphQL template deploy path.

See `references/healthcheck-path-override-limitation.md` for the full diagnosis chain.

## Pitfall: `serviceInstanceUpdate` Returns `true` But Doesn't Persist

```graphql
mutation {
  serviceInstanceUpdate(serviceId: "...", input: {
    healthcheckPath: null
    restartPolicyType: ON_FAILURE
  })
}
```

Returns `true` but `deployment.meta.fileServiceManifest.deploy.healthcheckPath` remains unchanged. Subsequent `serviceInstanceRedeploy` calls re-use the stale template config.

**Workaround**: Fix the root cause (repo config files, template serializedConfig), then delete + recreate the service.

## Pitfall: Root `railway.json` `healthcheckPath: ""` STILL Propagates

An empty string `""` is treated as "use framework auto-detection" which infers `/api/health` for known images. `null` may also not work as expected.

**Fix**: Omit `healthcheckPath` entirely from root `railway.json`:

```json
{
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Pitfall: Dockerfile COPY Paths Must Match rootDirectory

When template `source.rootDirectory = "clickhouse"`, the build context IS that directory. COPY paths in the Dockerfile must be **relative**, not include the prefix:

```dockerfile
# WRONG (double-nested):
COPY clickhouse/logs.xml /etc/clickhouse-server/config.d/logs.xml

# RIGHT (relative to clickhouse/):
COPY logs.xml /etc/clickhouse-server/config.d/logs.xml
```

**Symptom:** `failed to compute cache key: ... "/clickhouse/default-profile-low-resources-overrides.xml": not found`

**General rule:** When building `FROM <upstream>` Dockerfiles, **inspect the entrypoint** before assuming subcommands: `podman run --rm --entrypoint /bin/sh <image> -c "cat /entrypoint.sh"`. Verify COPY paths match the actual build context. Test CMD chains with `repr()` — never trust `cat` for operator visibility.

## Pitfall: CLI `railway deploy` Creates Duplicate Services

`railway deploy -t <code>` does NOT reuse existing services. It creates NEW services with randomized suffixes (`clickhouse-bHKB`, `plausible-ce-0_76`, `plausible-postgres-r8oJ`) and does NOT:
- Resolve `${{...}}` template var syntax (passes literal strings)
- Create volume mounts
- Set POSTGRES_PASSWORD or other required env vars

**Use case:** Only for validating Dockerfile source builds correctly. NOT for template variable testing.

**Cleanup:** `railway service delete -s <id> -y`

## Pitfall: Adding healthcheckPath Unnecessarily

**DO NOT add `healthcheckPath` to service configs unless you have verified the service actually needs a non-default check.**

Counter-intuitively, Railway does NOT force `/api/health` when no `healthcheckPath` is set. The service is considered healthy when its process starts. Adding `healthcheckPath: "/ping"` to ClickHouse **makes THINGS WORSE** because:
- If set at root level → propagates to ALL services (including those that don't have `/ping`)
- If set per-service → Railway still respects it but ClickHouse starts fine WITHOUT it

**The correct pattern (verified with `plausible-analytics-ce` reference template):**
```json
{
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```
NO `healthcheckPath` for ANY service.

**What about slow-starting services (ClickHouse, JVM)?**
- Increase `restartPolicyMaxRetries` to 10-15
- Do NOT set `healthcheckPath` just because it's slow
- The service is healthy when the process starts, even if it's not fully ready

## Pitfall: Root `railway.json` healthcheckPath Propagates to ALL Services

When the root `railway.json` specifies `healthcheckPath` in its `deploy` block, Railway's template generator bakes that path into the `serializedConfig` for **all** services — not just the root. This means ClickHouse (which only responds to `/ping`) gets `/api/health` and fails.

**Why this is insidious:** The template's serializedConfig looks correct when inspected — it shows per-service paths. But the deploy process reads from the GENERATED serializedConfig, not the per-service files. If root has a healthcheckPath, it propagates.

**The ONLY safe pattern:** Omit `healthcheckPath` from ALL railway.json files. Railway does NOT force `/api/health` when no path is set — services are considered healthy when their process starts.

Root `railway.json` (CORRECT):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

`clickhouse/railway.json` (CORRECT):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Symptom:** `Healthcheck failed!` for ClickHouse while service is actually running.

**Reference:** `agafonovim/railway-templates` — no `healthcheckPath` anywhere, all services deploy successfully.

See `references/healthcheck-path-override-limitation.md` for full details and failed workaround transcripts.

## Pitfall: Debugging Base Image Entrypoints

When Railway shows `exec: line N: <subcommand>: not found`:

1. Pull image: `podman pull <image:tag>`
2. Read entrypoint: `podman run --rm --entrypoint /bin/sh <image> -c "cat /entrypoint.sh"`
3. Identify which subcommands the entrypoint actually supports (look for `if [ "$1" = 'run' ]` chains)
4. Build CMD around those exact subcommands — anything else hits `exec "$@"` and fails

**Common pattern:** Entrypoints use `if/elif/else` chains. A "run vs migrate" split is common — `run` starts the app, `db migrate` runs schema updates. Both needed for correct startup.

See `references/plausible-ce-and-postgres-docker-patterns.md` for the Plausible v3.2.1 entrypoint transcript and correct `["/bin/sh", "-c", "/entrypoint.sh db migrate && /entrypoint.sh run"]` pattern.

## Pitfall: Config as Code Is Single-Service ONLY

`railway.toml` and `railway.json` (Config as Code) only support **one service** per file. The `[[services]]` array and `[services.plugins.*]` blocks do NOT create multiple services — Railway ignores everything after the first service or treats the whole file as one service's build/deploy config.

**Multi-service projects (app + postgres + clickhouse, etc.) REQUIRE Infrastructure as Code:**
```bash
railway config init          # creates .railway/railway.ts
# edit .railway/railway.ts to define all services + plugins
railway config plan          # preview
railway config apply         # create services
```

See `references/config-as-code-vs-iac.md` for full details and migration notes.

## Pitfall: CLI-Created Templates Have Empty Variables (But GraphQL Path Exists)

`railway templates create` CLI does not read `template-vars.json` or `template-editor-raw.json` from the repo. The resulting draft has `"variables": {}` in `serializedConfig`.

**Workarounds (pick one):**
1. (Preferred) Reuse old published template via `railway templates unpublish <code>` — variables pre-configured
2. Configure variables manually in dashboard template editor (editor reads template-vars.json)
3. **GraphQL build path** (NEW — session-proven 2026-07-08): Create services via `serviceCreate`, set variables via `railway variable set`, then `templateGenerate`. See `references/railway-graphql-template-introspection.md`.

## Pitfall: templateGenerate Strips Literal Variable Values

When `templateGenerate` reads project variables into `serializedConfig`, it **keeps** Railway-template-expression values (`${{...}}`) as `defaultValue` but **strips** literal values. So:

- `${{RAILWAY_PUBLIC_DOMAIN}}` → kept as `defaultValue`
- `${{secret(64)}}` → kept as `defaultValue`
- `${{plausible-postgres.DATABASE_URL}}` → kept as `defaultValue`
- `false`, `plausible`, `http://clickhouse:8123/plausible` → **stripped** (variable shows only `isOptional: false`)

**Fix:** Use a Railway expression for the default, OR set the literal value manually in the dashboard editor after generation.

## Pitfall: templateGenerate Fails Without `source connect`

`serviceCreate` with `source.repo` alone is insufficient. You MUST also run:
```bash
railway service source connect --repo owner/repo --branch main --service <ID>
```
Otherwise `templateGenerate` fails: "Service X does not have a source that can be used to generate a template".

## Pitfall: serviceInstanceUpdate Signature Quirk

`serviceInstanceUpdate` takes `serviceId` as a **separate top-level argument**, not inside `input`:
```python
# CORRECT:
graphql("""mutation ($serviceId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, input: $input)
}""", {"serviceId": "<ID>", "input": {"rootDirectory": "clickhouse", ...}})

# WRONG (will fail validation):
graphql("""mutation ($input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(input: $input)
}""", {"input": {"id": "<ID>", ...}})
```

Also: `ServiceUpdateInput` only accepts `icon` and `name`. Cannot update deploy config or rootDirectory — use `serviceInstanceUpdate` instead.

## Quick Diagnostic: Build Fails With "No Associated Build" → Then Healthcheck Fails

**BEFORE any other debugging**, check `railway.toml` syntax:

```bash
python3 -c "import tomllib; tomllib.load(open('railway.toml','rb')); print('TOML OK')"
grep -nE '^\w+ "[^"]*"$' railway.toml  # finds missing = signs
```

A single `key "value"` instead of `key = "value"` causes Railway to silently reject the entire file — the ONLY symptom is "Deployment does not have an associated build" with no build logs. See `references/first-step-toml-syntax-diagnostics.md` for details.

**If TOML is valid but healthcheck still fails:** app probably needs template vars that `railway up` CLI does NOT inject. See `references/cli-deploy-missing-template-vars.md`.

**CRITICAL: Python drives workflow. LLM fills small gaps only.**

User explicitly rejected "LLM-driven pipeline" where Python just orchestrates LLM decisions. The right architecture:
## Pre-Deploy Verification: Clean Slate Required

**Before `railway templates create`:**
1. Remove all manual var overrides from all services (`railway variable delete KEY --service <svc> ...` for stale credentials)
2. Re-deploy clean (`railway deployment redeploy --service <svc> --yes`)
3. Verify vars resolve cleanly (`railway variables --service <svc> --kv`)

**Why:** `railway templates create` regenerates `template-editor-raw.json` from the project's active variables. Any manual override (old `DATABASE_URL`, hardcoded `CLICKHOUSE_PASSWORD`) gets captured into template → leaks credentials → crashes future deploys.

## Testing: Drafts — CLI vs Dashboard

**CRITICAL: `railway templates create` requires the service to have a Docker image source.** If the project was deployed via `railway up` (Dockerfile build), the CLI fails with "Service X does not have a source that can be used to generate a template". See `references/templates-create-requires-image-source.md`.

```bash
# Check if service has an image source:
railway service list --json | python3 -c "
import sys,json; data=json.load(sys.stdin)
[print(s['name'], '→ source:', s.get('source','NONE')) for s in data]
"
```

### Path A: Dashboard (always works)
1. Open project in Railway dashboard → "Generate Template"
2. Creates unpublished draft from ANY deployed project (no image source needed)

### Path B: CLI (requires source — Docker image OR GitHub repo)

Only works if service has a source. Check:
```bash
railway service list --json | python3 -c "
import sys,json; data=json.load(sys.stdin)
[print(s['name'], '→ source:', s.get('source','NONE')) for s in data]
"
```

**⚠️ CLI-CREATED TEMPLATES HAVE EMPTY VARIABLES.** `railway templates create` does NOT read `template-vars.json` from the repo. The resulting draft's `serializedConfig.services.<id>.variables` is `{}`. You MUST configure variables through the dashboard editor before the deploy form works.

**Prefer reusing old published templates over CLI creation.** Check `publish-record.json` for old template IDs and `railway templates unpublish <code>` to convert to draft — old templates have variables pre-configured.

```bash
# Check for existing templates (may need GraphQL if not in CLI list)
cat publish-record.json  # old template IDs
railway templates list --json | python3 -c "..."  # workspace list
# Unpublish old template to reuse as draft
railway templates unpublish <code> --yes --json
```

**No source?** Connect GitHub repo first, then retry:
```bash
railway service source connect --repo <owner>/<repo> --branch main --service <name>
railway templates create --json   # now works
```

**Draft templates cannot be deployed via `railway deploy --template <code>`** — only published templates can be deployed through the marketplace URL. User must test via browser or publish first.

## New Pitfalls 2026-07 (from Plausible CE session)

### 0. railway.toml `key "value"` Syntax Kills All Builds (check FIRST)

**Symptom:** `railway up` succeeds indexing/upload but `railway status` shows "Failed" and `railway logs` says "Deployment does not have an associated build". No build logs at all.

**Root cause:** `railway.toml` uses `key "value"` (no `=`), which is invalid TOML. Railway silently rejects the file → no services defined → no build → no error about TOML.

**Fix:** Add `=` signs everywhere:
```toml
# WRONG
name "plausible"
# RIGHT
name = "plausible"
```

**Why this happens:** Hand-editing `.toml` files commonly drops `=`. This is the **FIRST** diagnostic step whenever a build fails with no logs. See `references/first-step-toml-syntax-diagnostics.md`.

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

**CRITICAL: Always get explicit user permission before `railway templates publish`.** User retains control over publication state. NEVER publish without explicit invitation like "publish now".

## New Project Bootstrap (for template testing)

```bash
# Create fresh project
PID=$(railway init --name <test-name> --json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Link + deploy generates service configs
cd <template-dir>
railway link --project $PID
railway up

# Now create draft from clean project
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

For plugin vars vs form vars (NEVER put plugin vars in deploy form), see `references/plugin-vars-vs-form-vars.md`.

For publish/draft/unpublish workflow and UX rules, see `references/template-form-ux-ux-and-workflow.md`.

**Publish Consent Rule:** User said multiple times: "do not publish template until issues fixed", "don't publish template without my consent". Keep template **draft** (UNPUBLISHED) until user explicitly asks to publish. Draft = files ready, not live. User publishes from dashboard when ready.

**Empty Form Fields Are Bad UX:** If plugin form shows empty textboxes with asterisks, user won't know what to fill. Resolution: remove the form entirely, not add labels. Plugin auto-injects all vars. See `references/template-form-ux-and-workflow.md`.

For CMD string pitfalls display-rendering traps, see `references/plausible-crash-malformed-cmd.md`.

For post-deploy crash loops plugin-backeddatabases (Postgres, ClickHouse)see`references/stale-credentials-plugin-rotation.md`.

For`${{Postgres.DATABASE_URL}}`macro pitfalls, multiple Postgres services, when use individual component vars, see`references/postgres-component-vars-vs-database-url.md`.

For class-level pitfalls learned recently — BASE_URL empty crashes app, manually overriding plugin-managed vars breaks deploys, two-file sync pitfalls — see`references/template-gotchas-pitfalls.md`.

**CMD verification after Dockerfile changed** (mandatory):
1. Count shell operators: `cat Dockerfile | sed -n '/CMD/p' | grep -c '&&'`must equal`N-1` for `N` chained commands.
2. Read raw bytes with `python3 -c "print(repr(open('Dockerfile').read()))"` — ONLY way confirm `&&` actually present; `cat` collapse rendering `&&` shows nothing on screen with no error.
3. Do NOT blindly pass arguments base-image `entrypoint.sh` — not all images support subcommands like `createdb`/`migrate`. Verify by extracting: `podman create --name tmp <image> && podman cp tmp:/entrypoint.sh - | tar xO`

**Plugin-backed service templates (Postgres, MySQL, ClickHouse)**:
- For dynamic credentials: **mandatory** use `${{...}}` references (never hardcodes). Prefer individual component vars (`${{Postgres.POSTGRES_USER}}`, `${{Postgres.POSTGRES_PASSWORD}}`, `${{Postgres.RAILWAY_PRIVATE_DOMAIN}}`, `${{Postgres.POSTGRES_DB}}`) over `${{Postgres.DATABASE_URL}}` — the macro goes stale when duplicate Postgres services exist. See `references/postgres-component-vars-vs-database-url.md`.
- For ClickHouse: companion service must set `CLICKHOUSE_DB` (missing default). Reference `${{clickhouse.CLICKHOUSE_USER}}`, `${{clickhouse.CLICKHOUSE_PASSWORD}}`, `${{clickhouse.CLICKHOUSE_DB}}` in `CLICKHOUSE_DATABASE_URL`.
- **Two-file sync rule**: Every template needs `template-vars.json` AND `template-editor-raw.json` per service, both with identical entries. Missing either causes silent deploy form issues. See `references/template-variable-patterns.md`.
- Multiple plugin services same type same project (e.g., `Postgres` + `Postgres-Q6IU`) cause `${{...}}` resolve empty strings silently — kill auth. Remove duplicates and re-verify ${Postgres.DATABASE_URL} resolves correctly.
- See `references/stale-credentials-plugin-rotation.md` for diagnosis flow.

**Verify credentials resolve correctly after setting vars**:

```bash
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

If resolved URL shows `postgresql://postgres:@:/` or `postgresql://user:@host:port/`, template var interpolation silently failed and auth will crash the consumer. Check for duplicate services first, then re-add missing `CLICKHOUSE_DB` etc. See `references/stale-credentials-plugin-rotation.md`.

5. When debugging a crashing service template, check `railway logs --service <name>` for the exact command that was executed. If the crash logs show `/entrypoint.sh createdb /entrypoint.shmigrate && /entrypoint.shrun` style malformed commands, the CMD is corrupted on disk.
6. When fixing, write the Dockerfile directly with python using explicit byte strings or heredocs rather than chaining `&&` inside a single `sh -c` argument where blanks around `&&` may be misinterpreted.

**LLM usage rules:**
- Step 1 uses 4 phases: USER → EXPOSE → HEALTHCHECK → verify (each separate small call)
- Worker runs FOREGROUND — background processes get SIGTERM killed, produce tcsetattr errors
- Use `stdin=subprocess.DEVNULL` in subprocess.run to avoid TTY issues
- User explicitly said: "want get quick response, not give big prompt"

**Template pipeline is generic.** No hardcoded per-app logic. Detect everything from Dockerfile:
- Image tag `-postgres-*` → Postgres required (no volume needed)
- Image tag `-sqlite-*` → standalone, add `/data` volume
- ENV DATABASE_URL → external DB required

## Template Naming (NO railway- prefix)

**User explicitly corrected multiple times: "not prefix railway_ project name"**

Template directories use app name directly:
- `open-webui/` not `railway-open-webui/`
- `keycloak/` not `railway-keycloak/`
- `umami/` not `railway-umami/`

Pipeline strips `railway-` prefix from argument if provided.

## Two-Variable-File System

| File | Fields | Purpose |
|------|--------|---------|
| `template-vars.json` | `defaultValue`, `description`, `isOptional` | Source of truth, pipeline validation |
| `template-editor-raw.json` | `value`, `description` | Deploy form published to marketplace |

`isOptional` does NOT appear in editor-raw format. Railway deploy form schema doesn't support optional vars.

## Volume Detection (Generic)

Detect service needs from image name/tag BEFORE build:
```python
# Pattern → service required
r':(?:postgresql|postgres|mysql|mariadb|redis|mongo)' → external DB
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

## Dedup Logic (Robust)

Normalize names before comparison:
```python
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```
Check substring match BOTH directions:
```python
if normalized in val or val in normalized:
```
    ```

    ## New Pitfalls 2026-07 (from Plausible CE session)

    ### 1. Plugin Forms Create Empty Textboxes

    **Symptom:** Plugin form shows empty boxes with asterisks:
    ```
    PGDATA * Value [empty]
    POSTGRES_DB * Value [empty]
    POSTGRES_USER * Value [empty]
    POSTGRES_PASSWORD * Value [empty]
    ```

    **User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

    **Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
    ```bash
    rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
    ```
    Clean companion-mapping.json (no `postgres` block):
    ```json
    {
      "clickhouse": {
        "CLICKHOUSE_USER": "CLICKHOUSE_USER",
        "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_DB": "CLICKHOUSE_DB"
      }
    }
    ```

    ### 2. Capturing Manual Overrides

    **Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

    **Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
    ```bash
    railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
    # should show 0 project-specific var overrides
    ```
    Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

    ### 3. PGDATA Path Gotcha

    Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
    ```
    PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
    ```

    **Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

    ## Verify Working Template

    After deploys:

    1. All 3 services Online:
    ```bash
    railway status | grep -E 'Online|Crashed|Failed'
    ```

    2. DATABASE_URL populated:
    ```bash
    railway variables --service plausible-ce --kv | grep DATABASE_URL
    # WRONG: postgresql://postgres:@:/plausible
    # RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
    ```

## Railway CLI Commands (Verified)

| Command | Purpose |
|---------|---------|
| `railway init --name X --json` | Create new project |
| `railway project link --project X` | Link directory to project |
| `railway up` | Deploy |
| `railway templates create --project ID` | Create draft template |
| `railway templates publish ID` | Publish to marketplace |

**NO** `railway project create` — use `railway init` instead.

## Step 0 Bootstrap

Pipeline creates starter Dockerfile if none exists. Don't fail on missing Dockerfile — bootstrap it.

## Draft-Only Publishing

**User explicitly said: "publish draft not all way production"**

Step 9 creates draft template only. Does NOT auto-publish to marketplace. Manual publish command provided to user.
|------|--------|---------|
| `template-vars.json` | `defaultValue`, `description`, `isOptional` | Source of truth, pipeline validation |
| `template-editor-raw.json` | `value`, `description` | Deploy form published to marketplace |

**isOptional only in template-vars.json.** template-editor-raw.json does NOT have isOptional field.

Pipeline auto-converts: `defaultValue` → `value`, drops `isOptional`.

## Volume Binding (Both Files Required)

Volume must be defined in BOTH:
- `railway.json`: `deploy.volumeMounts`
- `railway.toml`: `[[deploy.volumeMounts]]`

**Template updates only affect NEW deployments.** Existing services don't retroactively get volumes.

## Candidate Discovery (LLM Online Research)

**NO hardcoded candidate list.** User explicitly corrected: "don't research yourself, make pipeline"

LLM discovers candidates from live sources:
- Query: "Pick ONE popular Docker-ready self-hosted app NOT on Railway"
- Sources: awesome-selfhosted GitHub, Hacker News Show HN, r/selfhosted
- Constraints: >5000 stars, single container, MIT/BSD/Apache/AGPL license
- Returns JSON: `{"name": "...", "github": "...", "image": "...", "port": 3000, "db_needs": "none|postgres"}`

**Dedup is critical.** User corrected: "where dedup logic before?"

Dedup checks:
1. Exact normalized name match
2. Substring match either direction
3. Retry up to 5 times if LLM returns duplicate

## User Frustration Signals (STOP when these fire)

- "why doing pipeline work?" — agent went off-task
- "stop" — immediate halt
- "wait, let pipeline update X, not me" — user wants pipeline to do work, not agent
- "who decides candidates, research LLM, why fixed list?" — user rejected hardcoded approach
- "think will work?" — user skeptical, needs evidence not promises
- "revert first" — user wants undo
- "not prefix railway_ project name" — naming convention correction
- "sure it works?" — user wants verification, not claims

**When frustrated: STOP. Ask what user wants. Don't continue current approach.**

**Dedup:** Normalize names (lowercase, strip `railway-`/`railway_`, replace spaces/underscores/hyphens). Check substring match both directions against published templates.

## Project Directory Naming

**NO `railway-` prefix on local project folders.**

```bash
python scripts/pipeline.py umami      # correct
python scripts/pipeline.py keycloak   # correct
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

Pipeline auto-strips `railway-` or `railway_` prefix from argument.

## Step 9: Draft Only (No Auto-Publish)

**Pipeline does NOT live-publish.** Step 9 creates draft only. Manual `railway templates publish` required for marketplace.

## Volume Binding

Template updates only affect **NEW deployments**. Existing services don't retroactively gain volumes.

Volume config must exist in BOTH:
- `railway.json` (JSON format)
- `railway.toml` (TOML format)

Detect volume needs from Dockerfile/image:
- Tag contains `-postgres`/`-mysql` → external DB required, no volume
- Tag contains `-sqlite` or no DB → add `/data` volume

## Two-Variable-File System

| File | Fields | Purpose |
|------|--------|---------|
| `template-vars.json` | `defaultValue`, `description`, `isOptional` | Source of truth, pipeline validation |
| `template-editor-raw.json` | `value`, `description` | Deploy form published to marketplace |

Pipeline auto-converts: `defaultValue` → `value`, drops `isOptional`.

## Dedup Logic (Strong)

Before generate ANY files:

1. **Normalize**: lowercase, spaces/underscores/hyphens → single hyphen
2. **Exact match**: `name == slug` → duplicate
3. **Substring both directions**: `name in slug OR slug in name` → duplicate
4. **Strip version suffix**: `open-webui-3` normalizes to `open-webui`

On duplicate: HALT with "X already on Railway" message.

## Version Pinning Rule

**Always pin Dockerfile versions.**

```dockerfile
FROM ghcr.io/open-webui/open-webui:v0.10.2-slim  # pinned ✓
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

Auto-bump releases: edit Dockerfile `FROM` tag + republish.

Convention:
```dockerfile
# Umami v2.15.0 — bump when updating
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

## Two-Variable-File System

| File | Schema | Purpose |
|------|--------|---------|
| `template-vars.json` | `{NAME: {defaultValue, description, isOptional}}` | Canonical source |
| `template-editor-raw.json` | `{NAME: {value, description}}` | Deploy form |

`template-editor-raw.json` auto-generated from `template-vars.json` (drops `isOptional`). Never hand-edit. Pipeline step 7 regenerates both.

## Service Requirements Detection

Detect external service needs BEFORE build:

- Image tag `-postgresql-` or `-mysql-` → needs that DB (NOT bundled)
- Image tag `-sqlite-` → standalone (suppress DB warnings)
- Dockerfile `ENV DATABASE_URL=` → external DB required

Pipeline warns before build. User adds Postgres service → retry build.

## Volume Mount

`railway.json` and `railway.toml` MUST both declare same volumes. Step 8 validates match.

**Gotcha:** Template changes don't propagate to existing services. New deploy gets volume. Existing services need manual volume add.

## Worker (LLM) Calls

Local Hermes worker at `~/.local/bin/worker`. NOT pip-installable.

```bash
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

Pipeline pattern with hang fix:
```python
subprocess.run(
    ["worker", "-z", prompt],
    capture_output=True, text=True, timeout=600,
    stdin=subprocess.DEVNULL,  # prevents tcsetpgrp background hang
```
```

## New Pitfalls 2026-07 (from Plausible CE session)

### 1. Plugin Forms Create Empty Textboxes

**Symptom:** Plugin form shows empty boxes with asterisks:
```
PGDATA * Value [empty]
POSTGRES_DB * Value [empty]
POSTGRES_USER * Value [empty]
POSTGRES_PASSWORD * Value [empty]
```

**User complaint:** "Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"

**Fix:** Don't add labels. **Remove the form files entirely.** Plugin auto-injects everything:
```bash
rm -rf postgres/   # remove postgres/template-vars.json postgres/template-editor-raw.json
```
Clean companion-mapping.json (no `postgres` block):
```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

### 2. Capturing Manual Overrides

**Symptom:** After manually fixing `DATABASE_URL` in live project, new draft captures the override → future deploys crash.

**Rule:** Before `railway templates create`, remove all manual overrides from ALL services:
```bash
railway variables --service plausible-ce --kv | grep -v ^RAILWAY_
# should show 0 project-specific var overrides
```
Re-deploy clean: `railway deployment redeploy --service <svc> --yes`

### 3. PGDATA Path Gotcha

Manually set `PGDATA=/var/lib/postgresql/data/pgdata` crashes — Railway expects exact volume mount path:
```
PGDATA variable does not start with the expected volume mount path, expected to start with /var/lib/postgresql/data
```

**Fix:** Remove PGDATA entirely or match volume mount path exactly (no trailing paths).

## Verify Working Template

After deploys:

1. All 3 services Online:
```bash
railway status | grep -E 'Online|Crashed|Failed'
```

2. DATABASE_URL populated:
```bash
railway variables --service plausible-ce --kv | grep DATABASE_URL
# WRONG: postgresql://postgres:@:/plausible
# RIGHT: postgresql://postgres:***@postgres.railway.internal:5432/plausible
```

## New Pitfalls 2026-07-08 (from Plausible deploy fix session)

### `railway add --image` is NON-interactive (companion service workaround)

When IaC SDK doesn't resolve (`railway config plan` fails), and GraphQL `serviceCreate` mutations fail for services with `rootDirectory`, use `railway add --image` to create companion services from a Docker image:

```bash
# Creates ClickHouse service non-interactively (no prompts!)
railway add --image clickhouse/clickhouse-server:24.12-alpine -s ClickHouse
```

**Trade-off:** Uses base image, not the custom Dockerfile. Custom configs (COPY in Dockerfile) are skipped. For configs that can be set via env vars, set them after creation. For configs requiring files, accept the base image or use dashboard to switch source.

### `${{Postgres.DATABASE_URL}}` empty even on Postgres plugin service

`railway up` deploys don't resolve `${{...}}` macros. The Postgres plugin's `DATABASE_URL` may also be empty when queried via CLI. Construct manually from component vars:

```bash
# Get component vars from Postgres service
railway variables --service <postgres-id> --kv
# Shows: POSTGRES_USER, POSTGRES_PASSWORD, RAILWAY_PRIVATE_DOMAIN, POSTGRES_DB

# Construct DATABASE_URL:
DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${RAILWAY_PRIVATE_DOMAIN}:5432/${POSTGRES_DB}"

# Set on consumer service:
railway variables set --service <consumer-id> "DATABASE_URL=$DATABASE_URL"
```

### `railway service link <id>` is positional, not `--service <id>`

```bash
# CORRECT:
railway service link 8109fc95-1809-4aa0-9270-971a0a8b18ad

# WRONG:
railway service link --service 8109fc95-1809-4aa0-9270-971a0a8b18ad
# Error: unexpected argument '--service'
```

### `railway service redeploy` requires `--yes` in non-interactive mode

```bash
# Non-interactive (CI/scripts):
railway service redeploy --service <id> --yes

# Interactive (TTY):
railway service redeploy --service <id>  # prompts for confirmation
```

### GraphQL: `rootDirectory` goes INSIDE `source` object

When creating services via `serviceCreate` mutation, `rootDirectory` must be nested inside the `source` dict alongside `repo`:

```python
# CORRECT:
{"source": {"repo": "https://github.com/owner/repo", "rootDirectory": "clickhouse"}}

# WRONG (rootDirectory at top level → HTTP 400):
{"source": {"repo": "https://github.com/owner/repo"}, "rootDirectory": "clickhouse"}
```

### `serviceInstanceUpdate` returns scalar `Boolean!` — no subfields

The GraphQL `serviceInstanceUpdate` mutation returns `Boolean!`, not an object. Don't request subfields:

```graphql
# CORRECT:
mutation($serviceId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, input: $input)
}

# WRONG (causes GRAPHQL_VALIDATION_FAILED):
mutation($serviceId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, input: $input) { id }
}
```

### Practical multi-service deploy without IaC (hybrid CLI + GraphQL)

When IaC SDK doesn't resolve, the working pattern for multi-service (3+ services):

```bash
# 1. Postgres plugin — created via dashboard OR as side-effect when railway up detects
#    a Postgres dependency. railway add -d postgres is interactive (avoid in scripts).
# 2. Main service: railway service link <main-id> && railway up --detach
# 3. Companion service: railway add --image <image> -s <name>  # NON-interactive!
# 4. Set all env vars: railway variables set --service <id> KEY=VALUE ...
# 5. Redeploy if needed: railway service redeploy --service <id> --yes
# 6. Verify: railway status
```

## Step 1: 4-Phase Dockerfile Fix

Tiny prompts > single big rewrite:

| Phase | Trigger | Prompt |
|-------|---------|--------|
| 1/4 | USER missing/root | "Add non-root USER" |
| 2/4 | EXPOSE missing | "Add EXPOSE 8080" |
| 3/4 | HEALTHCHECK missing | "Add HEALTHCHECK" |
| 4/4 | verify | Python validates all 3 present |

Each fix independently verifiable. Fast + reliable.

## New Pitfalls 2026-07-08 (Template Variable Defaults — Definitive Findings)

### Dashboard Raw JSON Editor Is the ONLY Way to Set Variable Defaults

**Confirmed after exhaustive testing (CLI + GraphQL):** Neither `railway templates create` (CLI) nor `templateGenerate` (GraphQL) can produce a template with all variable defaults filled in. Both capture the project's runtime state where:
- `${{...}}` macros are resolved to concrete values (or empty strings)
- Literal values (`false`, `plausible`, `http://clickhouse:8123/plausible`) are stripped to NONE

**The ONLY working path:**
1. Create template via CLI or GraphQL (gets scaffold with empty/NONE variables)
2. Open dashboard editor's Raw JSON for each service
3. Paste the per-service variables JSON from local files (`plausible-ce.json`, `clickhouse/template-editor-raw.json`, etc.)
4. Template now has all defaults and deploys with one click

**Per-service JSON files (paste into matching service's `variables` key in Raw JSON):**
```
<template>/
├── plausible-ce.json              # → Plausible CE service variables
├── clickhouse/template-editor-raw.json  # → ClickHouse service variables
└── postgres/template-editor-raw.json    # → Postgres sibling service variables (NEW: parent-mount geometry)
```

**Sibling-service upgrade (2026-07-08):** The Railway `postgres-ssl:18` plugin was replaced by a sibling `postgres:16-alpine` service due to the ext4 `lost+found/` PGDATA-crash bug (see references/plausible-ce-and-postgres-docker-patterns.md § "Lost+Found Gotcha"). The sibling service uses a parent-mount geometry: volume mounted at `/var/lib/postgresql` (NOT `/var/lib/postgresql/data`), with `PGDATA=/var/lib/postgresql/data` as a subpath. This places the volume's lost+found/ at the volume root, outside PGDATA, where initdb sees an empty directory and proceeds.

### GraphQL Mutations Use `input` Wrapper Pattern

All template-related GraphQL mutations use `input` argument pattern, not direct arguments:

```graphql
# CORRECT — input wrapper:
mutation($input: TemplateDeleteInput!) { templateDelete(input: $input) }
mutation($input: TemplateGenerateInput!) { templateGenerate(input: $input) { id code name status serializedConfig } }

# WRONG — direct arguments (GRAPHQL_VALIDATION_FAILED):
mutation($id: ID!) { templateDelete(id: $id) { success } }
mutation($projectId: String!, $environmentId: String!) { templateGenerate(projectId: $projectId, environmentId: $environmentId) { ... } }
```

**TemplateDeleteInput format:** `{"input": {"id": "<template-id>"}}`
**TemplateGenerateInput format:** `{"input": {"projectId": "<id>", "environmentId": "<eid>"}}`

### Scalar Boolean! Mutations — No Subfields

Several mutations return scalar `Boolean!` — don't request subfields:

```graphql
# CORRECT (scalar returns):
mutation($input: TemplateDeleteInput!) { templateDelete(input: $input) }
mutation($input: VariableUpsertInput!) { variableUpsert(input: $input) }
mutation($input: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $input) }

# WRONG (requesting subfields on scalars → GRAPHQL_VALIDATION_FAILED):
mutation($input: TemplateDeleteInput!) { templateDelete(input: $input) { success } }
mutation($input: VariableUpsertInput!) { variableUpsert(input: $input) { name value } }
```

### Schema Introspection for Available Template Mutations

Use this query to discover all template-related mutations:

```graphql
query {
  __schema {
    mutationType {
      fields {
        name
        args { name type { name kind ofType { name kind } } }
      }
    }
  }
}
```

**Template mutations discovered (2026-07-08):**
- `templateClone` | `templateDelete` | `templateDeployV2`
- `templateGenerate` | `templatePublish` | `templateUnpublish`
- `templateVolumeUpdate` | `templateServiceSourceEject` | `sandboxTemplateBuild`

**There is NO `templateUpdate` mutation.** Template variables cannot be updated via API — dashboard editor only.

### `variableUpsert` Sets Vars But `templateGenerate` Doesn't Capture Them

Even when variables are set on the project via `variableUpsert` with `${{...}}` macro values, `templateGenerate` still produces NONE defaults. The backend resolves/strips values between upsert and generation. **Confirmed dead end.**

### Stale Draft Cleanup Workflow

Multiple failed template creation attempts leave duplicates. Clean up before creating fresh:

```bash
# List all drafts
railway templates list --json | python3 -c "import sys,json; [print(f\"{t['name']} | {t['code']} | {t['id']}\") for t in json.load(sys.stdin) if t.get('status') == 'UNPUBLISHED']"

# Delete all stale drafts for a given app
TEMPLATE_IDS=$(railway templates list --json | python3 -c "import sys,json; print(' '.join([t['id'] for t in json.load(sys.stdin) if t.get('code','').startswith('OOr') or t.get('code','').startswith('dSE') or t.get('code','').startswith('qYM') or t.get('code','').startswith('GWe')]))")
for id in $TEMPLATE_IDS; do railway templates delete "$id" --yes; done

# Then create one fresh template
railway templates create --project <id> --json
```

### Dashboard Editor: Per-Service Raw JSON ≠ Full Service Config

**The per-service Raw JSON editor only accepts environment variables** (`{ "value": "...", "description": "..." }` format). It does NOT accept `source`, `deploy`, `volumeMounts`, `icon`, or any other service-level config. These must be configured through the dashboard **UI widgets**:

| Setting | Where to Configure |
|---------|-------------------|
| `rootDirectory` | Service tile → Settings → Source → Root Directory |
| `volumeMounts` | Service tile → Add Volume → Mount Path + Size |
| `source` (repo/image) | Service tile → Settings → Source |
| `healthcheckPath` | Service tile → Settings → Healthcheck |
| `icon` | Service tile → icon field (URL input) |

**Symptom of confusion:** Pasting a full service JSON (with source/deploy/volume) into the per-service Raw JSON is silently rejected — only the `variables` key is stored.

**The root-level Raw JSON** (template-wide, not per-service) DOES accept `buckets` and the full `services` structure. See `railway-template-variables` skill for the full editor variable format reference.

### UI Widget Settings Don't Propagate to Marketplace Deploys

**Dashboard UI widget settings are ignored during marketplace deploys.** The serializedConfig (what the template actually deploys) only reflects root-level Raw JSON edits — not UI widget changes:

- `rootDirectory` set via widget → `null` in serializedConfig → wrong Dockerfile built
- `volumeMounts` set via widget → not in serializedConfig → no volume
- `icon` set via widget → not in serializedConfig → no icon

**Fix:** Edit root-level Raw JSON directly for these settings. See `railway-template-variables` skill for detailed table.

### Service Icons: `simpleicons.org` URLs Don't Work — Use Raw GitHub

**`https://simpleicons.org/icons/<name>.svg` returns HTML, not raw SVG.** This appears as a broken/default placeholder icon (e.g., SourceForge). Use the raw GitHub CDN instead:

```
# WRONG (serves HTML):
https://simpleicons.org/icons/plausibleanalytics.svg

# RIGHT (raw SVG):
https://raw.githubusercontent.com/simple-icons/simple-icons/master/icons/plausibleanalytics.svg

# Railway's own CDN (preferred for Railway services):
https://devicons.railway.app/i/clickhouse.svg
https://devicons.railway.app/i/postgresql.svg
```

**Custom icons** committed to the template repo can be referenced via raw GitHub URL:
```
https://raw.githubusercontent.com/<owner>/<repo>/main/template-icon.svg
```

### `template create` Wipes Dashboard Fixes — Never Regenerate

Regenerating a template (`railway templates create --project <id>`) reads the project's **runtime state** and destroys all dashboard editor fixes (buckets, variable defaults, icons, rootDirectory). **Generate once, then only use the dashboard editor.** See `railway-template-variables` skill for full details.

### Template Macro Resolution Matrix (Marketplace Deploys)

Confirmed across three deploy tests (positive-kindness, divine-laughter, hospitable-wisdom):

| Macro | Resolves? |
|-------|:---:|
| `${{RAILWAY_PUBLIC_DOMAIN}}` | ✅ Domain only |
| `${{secret(N)}}` | ✅ Random value |
| `${{Postgres.DATABASE_URL}}` | ❌ Empty |
| `${{Postgres.POSTGRES_*}}` | ❌ Empty |
| `${{clickhouse.CLICKHOUSE_*}}` | ❌ Empty |

**Key insight:** Only template-native macros resolve. ALL cross-service references (Postgres plugin vars, ClickHouse companion vars) resolve to empty. This affects every template with companion databases.

**Verified template fix:** `https://${{RAILWAY_PUBLIC_DOMAIN}}` prefix works — confirmed in hospitable-wisdom deploy. See `railway-template-variables` skill for full macro reference.

## Template Publish Flow (NOT automate)

1. Build+test locally (step 4)
2. Git commit+push (step 5)
3. Create draft `railway template create` (step 9)
4. User opens template editor URL, reviews
5. User runs manually: `railway templates publish <code> --category "AI/ML" --description "..." --readme-file README.md`

Pipeline NEVER auto-publishes. User must manually trigger.
```
