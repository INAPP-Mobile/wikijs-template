---
type: reference
title: "End-to-End Template Verify-Reissue Cycle (Plausible Pattern)"
---

## Purpose

Walkthrough end-to-end workflow we used to get a multi-service template (Postgres plugin + ClickHouse companion + Plausible CE) from crash loop to live. Recurring pattern for future Railway template work.

## Phase 1 — Fix Dockerfile correctly

**Critical:** Do NOT pass `&&` through heredocs or Python string escaping. The `&&` byte sequence collapses in terminal renders, `cat` shows nothing, but the shell sees a broken chain and crashes immediately on startup.

Correct write method (verified bytes):

```bash
printf '...\nCMD ["/bin/sh", "-c", "/entrypoint.sh migrate && /entrypoint.sh run"]\n' > Dockerfile
```

Verify ALWAYS with bytes, not renders:

```bash
od -c Dockerfile | grep -A2 CMD
# OR
python3 -c "print(repr(open('Dockerfile').read()))"  # only way to confirm actually <<pipe>><<pipe>> present
```

Do NOT assume `&&` exists — `cat`, `hexdump`, and Python display all collapse the bytes. `od -c` is ground truth.

## Phase 2 — Base-image entrypoint.sh inference

Never guess `entrypoint.sh` semantics. Extract directly:

```bash
mkdir -p /tmp/inspect && cd /tmp/inspect
podman create --name tmp <image> && podman cp tmp:/entrypoint.sh - | tar xO
```

Template image's built-in command semantics:
- `run` → start server
- `db migrate` → run migrations
- `db create` → create database
- Do NOT pass `createdb`/`migrate` directly; pass `db migrate` via `entrypoint.sh`

## Phase 3 — Plugin vs. companion vs. user vars

Triage every env var category:

| Category | Source | Where appears |
|----------|--------|---------------|
| **Plugin-managed** (Postgres plugin) | Railway auto-injects | NO form. `DATABASE_URL`, `POSTGRES_USER`, etc. |
| **Companion-managed** (ClickHouse companion) | Companion service vars | Companion's own `template-editor-raw.json` |
| **User-managed** | User fills during deploy | Main service's `template-editor-raw.json` |

**Rule:** NEVER put plugin-managed vars in `template-editor-raw.json`. Including them overrides auto-injection → stale credentials or empty strings on deploys.

## Phase 4 — companion-mapping.json wiring

Maps companion service vars so main service can reference them:

```json
{
  "postgres": { "DATABASE_URL": "DATABASE_URL" },
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

Main service references via `${{clickhouse.CLICKHOUSE_USER}}` etc.

## Phase 5 — Per-service JSON files

Every service gets two JSON files in its subdirectory:

```
service-name/
├── Dockerfile
├── template-vars.json          # pipeline source of truth (defaultValue format)
└── template-editor-raw.json    # deploy form (value format)
```

The subdirectory lives next to the main service, NOT in root.

## Phase 6 — Publish → test → unpublish loop

1. Fix all files upstream committed
2. Create draft: `railway templates create --project <id> --json`
3. Publish: `railway templates publish <CODE> --category "..." --description "..." --readme-file README.md`
4. Deploy new project via public URL, watch each service boot status
5. Re-publish template after fixes (`update` semantics; `railway templates re-publish ...`)
6. If you need to take it down: `railway templates unpublish <CODE> --yes`
7. Re-publish later after more fixes

**Do NOT publish before verifying a fresh deploy with real traffic.** Railway publish immediately live deploys real users.

## Phase 7 — Crash triage checklist

When service crashed after deploy, pull these in order:

1. `railway deployment list --service <name>` — which deployment failed
2. `railway logs --service <name> --tail 50` — actual crash backtrace
3. `railway logs --service <failed-dependency> --tail 50` — cascading crash (postgres crashed first?)
4. `railway variables --service <name> --kv 2>&1 | grep DATABASE_URL` — empty? plugin not injecting
5. `railway variables --service <plugin-component> --kv | grep <VAR>` — plugin itself crashed?

## Phase 8 — Duplicate service detection

When `${{...}}` macros resolve to empty strings:

1. `railway service ls` → look for duplicate names (`Postgres` + `Postgres-Q6IU`)
2. Remove duplicates: `railway service delete --service <dupe> --yes`
3. Re-deploy; macro resolves correctly

## Phase 9 — Base-image entrypoint.sh do-not-trust list

Do NOT trust image entrypoint subcommands without extraction. Plausible v3.2.1 entrypoint.sh format:

```
/entrypoint.sh run              → start server
/entrypoint.sh db migrate       → run migrations (NOT /entrypoint.sh migrate)
/entrypoint.sh db create        → create DB            (NOT /entrypoint.sh createdb)
```

Pass `db migrate` via `entrypoint.sh db migrate`, NOT `/entrypoint.sh migrate`. Wrong form → `createdb: not found` crash.

## Phase 10 — Hardcoded credential audit

Before every publish, scan template-editor-raw.json files for hardcoded passwords. Plugin auto-rotates passwords, so any literal string becomes stale.

Acceptable: `${{secret(N)}}` auto-generate, `${{clickhouse.*}}` companion var reference.
Unacceptable: `clickhouse_plausible_pw_2026` literal.
