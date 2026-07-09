# Session Reference: Kanboard Railway Template — QA Project Name Issue

Date: 2026-06-26
Repo: INAPP-Mobile/railway-kanboard

## Problem

Published a Kanboard Railway template, but the marketplace slug came out as `kanboard-qa-test` instead of just `kanboard`.

## Root Cause

Railway derives the template slug from the **project name**, not the GitHub repo name. The project used for QA/testing was named `kanboard-qa-test`, so `railway templates create` produced a slug of `kanboard-qa-test`.

## Fix Options

1. **Rename in the Railway Dashboard template editor** — fastest fix for an already-published template
2. **Create a new project** with the desired name (`kanboard` or `railway-kanboard`), link the same repo, deploy, then `templates create` from that project

## Published Template

- Slug: `kanboard-qa-test` (wanted: `kanboard`)
- Deploy URL: https://railway.com/deploy/kanboard-qa-test
- Service URL: https://kanboard-qa-test-production.up.railway.app
- Category: Starters

## E2E Test Results

All critical tests passed: GitHub deploy, healthcheck, login/auth, SQLite data persistence, PORT env override, template publish. See `pipeline-logs/e2e-kanboard-results.md`.

## Prevention Baked Into Pipeline Docs

These fixes were applied to `goal.md` and `guide.md` after this session:

1. **Self-cleaning first agent** — The Researcher (Agent 1) now has a "Pre-Flight: Clean the Board" step that runs `hermes kanban delete --status done --yes` before any research, so every pipeline starts fresh.

2. **Project name warning at deploy time** — The Deployer step now warns to use `--name <desired-slug>` when creating the Railway project, with a concrete wrong/right example.

3. **Project rename check before publish** — The Publisher step now runs `railway project rename` if the project name doesn't match the intended template slug.

4. **Teardown after publish** — The Publisher destroys the deployed project after successful publication (`railway project delete --yes`) to avoid running costs. The template remains live on the marketplace.

## Skill Additions

- `railway-deployment` skill gained pitfall #10 (first agent cleans board) and #11 (`--goal` is a boolean flag, not a path), plus a Step 3: Teardown in the template publishing workflow.
