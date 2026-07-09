# 2026-06-29 — Dev Task Decomposition: Template Pipeline

## Session Summary
User asked to break the monolithic Development task into smaller phases. The original dev-body.txt had 8 steps covering project scaffolding, asset creation, documentation, and verification. Result: 3 focused Dev tasks.

## Original Monolithic Task (dev-body.txt — deleted)
Steps crammed into one agent:
1. mkdir + cd into project dir
2. git init + git remote add
3. Create Dockerfile, railway.json, railway.toml, .env.example
4. Create template-icon.svg, og-image.svg
5. Write README.md
6. git add/commit/push
7. Save log
8. Verify with podman build + run + curl health

**Problem:** Too many concerns in one task. If Dockerfile had a syntax error, the agent would waste time on assets and docs before discovering the failure.

## Decomposed Tasks

### Dev-1: Scaffold (dev-scaffold.txt)
**Scope:** Project infrastructure — directory, git, Dockerfile, railway config, .env.example
**Key outputs:**
- Dockerfile (pinned version, no :latest, healthcheck)
- railway.json (build/start commands, healthcheck path)
- railway.toml (if needed)
- .env.example (documented env vars)
- Git repo with initial commit

**Acceptance criteria:**
- `podman build -t test .` exits 0
- All config files present and valid

### Dev-2: Assets & Docs (dev-assets.txt)
**Scope:** Visual assets and documentation — icons, README
**Key outputs:**
- template-icon.svg (800×800) — gallery card icon
- og-image.svg (1200×630) — social preview image
- README.md with required sections:
  - Deploy on Railway button
  - One-line description
  - Features list
  - Architecture overview
  - Environment variables table
  - Troubleshooting section

**Acceptance criteria:**
- SVG files valid (parseable)
- README has all 6 required headings for Railway templates

### Dev-3: Verify (dev-verify.txt)
**Scope:** Local build and health verification
**Key outputs:**
- podman build success (exit 0)
- podman run + curl health check (HTTP 200)
- Config validation (no :latest, no hardcoded secrets)
- Report saved to pipeline-logs/dev-verify-TEMPLATE_NAME.md

**Acceptance criteria:**
- Build: exit 0
- Health check: HTTP 200
- Startup: <30s
- Memory: <512MB
- No security issues

## Chain Flow

```
QA Gate → Dev-1 (Scaffold) → Dev-2 (Assets) → Dev-3 (Verify) → E2E Testing
```

Each task's FIRST ACTION creates the next via `create-next-card.sh`. The chain is pre-wired and survives agent crashes.

## When to Split vs Keep Together

**Split when:**
- Task has >5 steps
- Steps have different concerns (infra vs docs vs QA)
- Failure in early steps shouldn't waste time on later steps
- Different agents/persons could specialize

**Keep together when:**
- Steps are tightly coupled (can't build without docs)
- Task is <5 steps
- No conditional logic between steps
- Single concern/skill set required

## Related References

- `references/2026-06-29-railway-template-kanban-pipeline.md` — Full pipeline overview (10 stages)
- `references/2026-06-29-template-deploy-verify-pattern.md` — D3 deploy verification pattern
- `references/2026-06-29-service-vs-template-variables.md` — Service vs template variables
