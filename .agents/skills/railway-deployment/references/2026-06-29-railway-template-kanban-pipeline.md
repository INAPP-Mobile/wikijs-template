# Railway Template Pipeline — Kanban Workflow Reference

## Overview
This project uses a **multi-stage Kanban pipeline** on the `railway-template` board to manage the full lifecycle of Railway template creation, testing, and publication. Each template goes through a sequence of dependent tasks.

---

## Pipeline Stages (Cards)

| Stage | Card Title Pattern | Assignee | Purpose |
|-------|-------------------|----------|---------|
| **Research** | `Research: Identify Trending Candidates` | `worker` | Find 5 trending self-hosted apps missing Railway templates |
| **QA Gate v1** | `QA Gate v1: Validate Research Candidates` | `worker` | Score & filter candidates against dedup, complexity, demand |
| **Dev-1: Scaffold** | `Dev-1: Scaffold: [WINNER] Railway Template` | `worker` | mkdir, git init, Dockerfile, railway.json/toml, .env.example, commit/push |
| **Dev-2: Assets & Docs** | `Dev-2: Assets & Docs: railway-<name>` | `worker` | template-icon.svg, og-image.svg, README.md, commit/push |
| **Dev-3: Verify** | `Dev-3: Verify: railway-<name>` | `worker` | podman build + run + curl health, validate configs, report |
| **E2E Testing** | `E2E Testing: railway-<name>` | `worker` | Deploy, verify health, test functionality |
| **D1: Create Draft** | `D1: Create Draft: railway-<name>` | `worker` | Set service vars on source project → `railway templates create` → record TEMPLATE_ID |
| **D2: Configure & Publish** | `Configure & Publish: railway-<name>` | `worker` | Document manual var config → `railway templates publish` → record TEMPLATE_CODE |
| **D3: E2E Deploy Verify** | `E2E Deploy Verify: railway-<name>` | `worker` | Deploy as end-user (`railway deploy --template`) → health check → screenshots → report |
| **Publication** | `Publication: railway-<name>` | `worker` | Final metadata update, marketplace listing |

---

## Card Creation Script

The pipeline uses a **dedup-aware card creator** that reads raw body content from `pipeline-bodies/` files:

```bash
# /var/home/ihshim523/Work/railway/pipeline-bodies/create-next-card.sh
bash create-next-card.sh <PARENT_ID> <TITLE> <IGNORED> <BODY_FILE> [TEMPLATE_NAME]
```
**Body files in `pipeline-bodies/`:**

| File | Purpose |
|------|---------|
| `research-body.txt` | Research task instructions |
| `qa-body.txt` | QA Gate v1 (validation) |
| `dev-scaffold.txt` | Dev-1: Scaffold project (Dockerfile, railway.json, .env.example) |
| `dev-assets.txt` | Dev-2: Assets & Docs (icons, README) |
| `dev-verify.txt` | Dev-3: Verify (podman build/run/health) |
| `e2e-body.txt` | E2E testing |
| `deploy-draft.txt` | D1: Create template draft from source project |
| `deploy-publish.txt` | D2: Configure vars in dashboard, publish template |
| `deploy-verify.txt` | D3: Deploy as end-user, verify health, capture screenshots |
| `pub-body.txt` | Final publication metadata |

**Key features:**
- Reads body content **raw** (no interpretation)
- Substitutes `TEMPLATE_NAME` and `TEMPLATE_REPO` placeholders
- **Dedup check**: Skips if child with same title already exists (prevents duplicates on agent restart)
- Inherits parent's priority and assignee

---

## Publication Body (`pub-body.txt`) — Current Correct Version

```bash
# Step 1: Create template from project
TEMPLATE_ID=$(railway templates create --project TEMPLATE_NAME --json | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# Step 2: MANUAL - Configure template variables in web dashboard (REQUIRED)
# Template variables (descriptions, required/optional, secret() functions, defaults)
# CANNOT be configured via CLI or GraphQL — only in the web dashboard.
# Open: https://railway.com/workspace/templates
# Click your draft template → Variables tab → for each service/variable:
#   - Toggle Required ✅/❌
#   - Set Default value (use {{secret(32)}} for secrets)
#   - Add Description
# Save, then continue.

# Step 3: Publish to marketplace
railway templates publish "$TEMPLATE_ID" \
  --category Storage \
  --description "TEMPLATE_NAME - self-hosted solution deployable on Railway" \
  --readme-file README.md \
  --image "https://raw.githubusercontent.com/INAPP-Mobile/railway-TEMPLATE_NAME/main/template-icon.svg" \
  --json
```

**Key fixes from earlier broken version:**
| Old (Broken) | New (Correct) |
|--------------|---------------|
| `railway template publish` (singular) | `railway templates publish` (plural) |
| `--name` flag | Removed |
| `--repo` flag | Removed |
| `--image template-icon.svg` (local) | `--image "https://raw.githubusercontent.com/..."` |
| Missing `--category` | Added `--category Storage` |
| Missing `--readme-file` | Added `--readme-file README.md` |
| No `templates create` step | Added 2-step: create → publish |
| No variable config step | **Added manual dashboard step (Step 2)** |

---

## Pre-Flight: Clean the Board

First agent in pipeline **must** archive stale `done` tasks:

```bash
hermes kanban list --status done | grep "^✓" | awk '{print $2}' | xargs -r hermes kanban archive
```

**Note:** `hermes kanban delete` does NOT exist. Use `archive` per-task.

---

## Dev Task Decomposition

The Development phase was split from a single monolithic "Development" task (8+ steps) into 3 focused tasks to isolate concerns and enable partial re-runs:

| Task | Input | Output | Why Split |
|------|-------|--------|-----------|
| **Dev-1: Scaffold** (`dev-scaffold.txt`) | Winner name from QA | Git repo with Dockerfile, railway.json/toml, .env.example | Isolates infrastructure code; if Dockerfile has syntax error, only Dev-1 re-runs |
| **Dev-2: Assets & Docs** (`dev-assets.txt`) | Repo with working Dockerfile | template-icon.svg, og-image.svg, README.md | Isolates documentation; can be done by a different agent/person |
| **Dev-3: Verify** (`dev-verify.txt`) | Repo with all files | podman build/run/health check report | Validates the scaffold before E2E testing |

**Chain flow:** QA → Dev-1 → Dev-2 → Dev-3 → E2E (each creates the next via `create-next-card.sh`)

**Why not one task?** The monolithic Dev task crammed 8 steps together. Splitting allows:
- Dev-1 fails → retry only Dev-1 (don't waste time on assets)
- Dev-2 fails → retry only Dev-2 (don't rebuild container)
- Dev-3 fails → retry only Dev-3 (don't regenerate code)
- Different agents can specialize (container specialist, technical writer, QA)

## Deployment Task Decomposition

The deploy stage was split from a single monolithic "Deployment" task into 3 focused tasks to isolate concerns and enable partial re-runs:

| Task | Input | Output | Why Split |
|------|-------|--------|-----------|
| **D1: Create Draft** (`deploy-draft.txt`) | Source project with env vars set | TEMPLATE_ID | Isolates draft creation; if draft fails, only D1 re-runs |
| **D2: Configure & Publish** (`deploy-publish.txt`) | TEMPLATE_ID | TEMPLATE_CODE | Isolates the manual step; agent documents what to configure, then publishes |
| **D3: E2E Deploy Verify** (`deploy-verify.txt`) | TEMPLATE_CODE | Deployed project + screenshots | Isolates verification; if deploy fails, only D3 re-runs |

**Chain flow:** QA → Dev-1 → Dev-2 → Dev-3 → E2E → D1 → D2 → D3 → Publication (each creates the next via `create-next-card.sh`)

**Full pipeline (10 stages):**
```
Research → QA → Dev-1 (Scaffold) → Dev-2 (Assets) → Dev-3 (Verify) → E2E → D1 (Draft) → D2 (Publish) → D3 (Verify) → Publication
```

**Why not one task?** The monolithic deploy crammed 6 phases together. Splitting allows:
- D1 fails → retry only D1 (don't re-publish)
- D3 fails → retry only D3 (don't re-create draft or re-publish)
- Manual step in D2 is clearly documented and isolated

**Each task's FIRST ACTION** is to create the next task via `create-next-card.sh`. The chain is pre-wired and survives agent crashes.

---

## Common Pitfalls in Pipeline

1. **Token auth** — Use **Account Token** (`railway_...` from https://railway.com/account/tokens) for GraphQL mutations. Session tokens (UUID from `railway login`) expire ~24h.

2. **Template slug** — Derived from **project name** at `templates create` time, not repo name. Create project with desired slug name.

3. **Variables** — Template variable configuration (descriptions, required/optional, `secret()`, `randomInt()` functions, defaults) **can ONLY be done in the web dashboard template composer**. The CLI `railway templates publish` and GraphQL `templatePublish` mutation **accept metadata only** (category, description, image, readme, workspaceId). No CLI flags or GraphQL inputs exist for variable configuration.

4. **README sections** — Must have 6 exact headings: `# Deploy and Host`, `## About Hosting`, `## Why Deploy`, `, `, `## Common Use Cases`, `## Dependencies for`, `### Deployment Dependencies`

5. **Icon URL** — Must use `https://raw.githubusercontent.com/...` (NOT `github.com/.../raw/...`)

6. **Category** — Must be one of: AI/ML, Analytics, Authentication, Automation, Blogs, Bots, CMS, Observability, Other, Starters, Storage, Queues

7. **Description** — Hard limit 75 characters

---

## Pipeline Logs Directory

```
/var/home/ihshim523/Work/railway/pipeline-logs/
  ├── research-output.md
  ├── qa-output-*.md
  ├── dev-output-<template>.md
  ├── e2e-output-<template>.md
  ├── deploy-draft-<template>.md
  ├── deploy-publish-<template>.md
  ├── deploy-verify-<template>.md
  ├── pub-output-<template>.md
  └── <template>-code.txt
```

---

## Related References

- `references/2026-06-29-template-variable-config-dashboard.md` — Variable config is dashboard-only
- `references/2026-06-29-template-variables-cli-graphql-confirmation.md` — CLI/GraphQL confirmation (no automation possible)
- `references/2026-06-29-railway-template-graphql-mutations.md` — Full GraphQL mutation reference
- `references/2026-06-29-stirling-pdf-deploy-button-fix.md` — Template code/slug handling
- `references/2026-06-28-plausible-icon-url-fix.md` — Icon URL format requirement
- `references/2026-06-29-template-queue-system.md` — Sequential multi-template queue for batch publishing