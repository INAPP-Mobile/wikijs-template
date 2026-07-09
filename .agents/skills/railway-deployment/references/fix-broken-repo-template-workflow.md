# Fix and Draft-Template a Broken GitHub Repo

Walkthrough of identifying and fixing a broken repo template, then creating a draft template end-to-end. Based on Plausible CE fix (2026-07-08).

## Pre-Fix: Confirm Before Acting

User pointed at specific repo. **Look THERE first** — pull the repo's `railway.toml`, validate, trace the actual failure. Don't go creating new projects until you've ruled out the README-level problem.

```bash
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/main/railway.toml
python3 -c "import tomllib; tomllib.load(open('railway.toml','rb')); print('TOML OK')"
```

## Step 1 — Fix Root Cause

Common #1: `key "value"` → `key = "value"` (invalid TOML). Railway silently rejects entire file → "Deployment does not have an associated build" with no build logs.

```bash
# After fixing:
git add railway.toml
git commit -m "fix: railway.toml syntax (key = value format)"
git push origin main
```

## Step 2 — Deploy From Repo (Build Validates)

```bash
# Fresh project
railway init --name <app>-draft --json     # capture PID
cd <repo-dir>
railway link --project <PID>
railway up --detach --json
```

Build succeeds only if TOML + Dockerfile both valid. If "no associated build" again → TOML still broken.

**NOTE on multi-service repos:** If `railway.toml` defines multiple `[[services]]` with plugins, **only ONE service is created** — Config as Code is single-service only. You MUST use IaC (`.railway/railway.ts`) for multi-service projects. See `references/config-as-code-vs-iac.md`.

## Step 3 — Connect GitHub Source (CLI Enabler)

```bash
railway service source connect --repo <owner>/<repo> --branch main --service <name> --json
# → source switches from null to the repo
```

This makes `railway templates create` CLI work without dashboard access.

## Step 3.5 — Check for Existing Published Template (Reuse if Possible)

Before creating a new template, check if an old published version already exists with correct variables:

```bash
# Check publish-record.json for old template ID/code
cat publish-record.json
# Check workspace templates via CLI (may not show archived)
railway templates list --json | python3 -c "import sys,json; [print(f\"{t['code']} - {t['name']} ({t['status']})\") for t in json.load(sys.stdin) if '<app>' in t.get('name','').lower()]"
# Or query by ID directly via GraphQL (see references/railway-graphql-template-queries.md)
```

**If old template found:** `railway templates unpublish <code> --yes --json` → converts to draft with variables pre-configured. Skip step 4.

**Why prefer reuse:** Old templates already have correct `serializedConfig` (proper variables, auto-resolved service references). CLI-created templates have EMPTY variables that need manual configuration.

## Step 4 — Create Draft (Crashing OK) — Skip if Step 3.5 Reused Old Template

```bash
railway templates create --json
# → { id, code, editorUrl, status: "UNPUBLISHED" }
```

**WARNING:** CLI-created draft has **empty variables** in `serializedConfig`. You MUST configure variables through the dashboard editor (Step 5) before the template is usable.

**Crashing doesn't block draft creation.** The template form is independent of app health.

## Step 5 — Open Editor, Verify Form

Navigate to the `editorUrl` to check:
- Display name (sentence case, per AGENTS.md rule)
- Category, description
- Deploy form variables match `template-vars.json` (no plugin-managed vars leaking in)
- Icon is image-only (no text, per AGENTS.md rule)

## Step 6 — Clean Up Test Projects

```bash
# Delete test projects after draft is created
railway delete --project <PID> --yes
```

## User Rules (AGENTS.md)

These are project-specific and must be followed:
1. **Image-only icons** — template display icons must NOT contain text; only graphical icons matching existing style
2. **Sentence case display names** — "Plausible CE" not "plausible-ce" or "plausible ce"
3. **Never publish until fully fixed** — keep as draft, fix all issues, verify with fresh deploy before publish to marketplace

## Pitfall: This Session's Near-Miss

Multiple turns were wasted creating new projects (plausible-fixed, plausible-v3, plausible-blank) and tweaking configs, when the root cause was a single `key "value"` → `key = "value"` typo in the original repo. The fix took 1 character. **Always start by inspecting the user-provided source before exploring tangential fixes.**
