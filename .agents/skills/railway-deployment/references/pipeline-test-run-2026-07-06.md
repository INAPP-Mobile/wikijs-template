# Pipeline Test Run — 2026-07-06

## Test Target: umami (ghcr.io/umami-software/umami:postgresql-v2.15.0)

### Steps Completed
| Step | Result | Notes |
|------|--------|-------|
| 0 Bootstrap | OK | Created starter Dockerfile, detected blockers |
| 1 Dockerfile | OK | Fixed USER, EXPOSE, HEALTHCHECK (4 phases) |
| 2 .env.example | OK | 3 lines parsed from Dockerfile |
| 3 Icons + README | OK | Deterministic icons, LLM README |
| 4 Build | OK | Build succeeded, container needs Postgres |
| 5 Commit | OK | |
| 6 Deploy | PARTIAL | `railway init` works, link needs project ID |
| 7 Vars | OK | |
| 8 Pre-publish | OK | |
| 9 Draft | BLOCKED | Needs project ID from `.railway/project.json` |

### Issues Found

1. **Background process killed**: Worker runs in background → SIGTERM after 600s. Must run foreground or accept long wait.
2. **`railway project create` doesn't exist**: Use `railway init --name X --json` instead.
3. **Step 9 needs project ID**: Read from `.railway/project.json` after `railway init`.
4. **Container needs Postgres**: Umami image requires external Postgres. Build passes but container won't start standalone.

### Fixes Applied
- Step 6: Changed `railway project create` → `railway init --name X --json`
- Step 9: Read project ID from `.railway/project.json` instead of name
- Step 0: Bootstrap creates starter Dockerfile if missing
- Step 1: Added Phase 0 to pin `:latest` tags

### Pipeline Files (13 total)
```
scripts/pipeline/
├── __init__.py         orchestrator, prefix stripping
├── core.py             LLM calls, file helpers, colors
├── step_0_research.py  bootstrap + dedup
├── step_1_dockerfile.py 4-phase LLM fix
├── step_2_env_example.py deterministic
├── step_3_icons_readme.py icons (det) + README (LLM)
├── step_4_build_test.py podman build + health check
├── step_5_commit_push.py git
├── step_6_deploy.py    auto-link project
├── step_7_vars_template.py
├── step_8_pre_publish.py
├── step_9_publish.py   draft-only
└── step_10_teardown.py
```

### User Corrections This Session
- "not prefix railway_ project name" → strip prefix
- "publish draft not all way production" → draft-only
- "want get quick response, not give big prompt" → small LLM phases
- "don't think open-webui anymore, job pipeline now" → focus on pipeline
- "revert first" → reverted LLM-driven pipeline experiment
- "who decides candidates, research LLM, why fixed list?" → use curated list + dedup
- "pipeline create dockerfile, wasn't creating one?" → step 0 bootstraps
- "why update unami dockerfile?" → don't recreate, preserve progress
- "don't get confused" → stay focused on current task
- "stop misunderstand" → stop over-engineering
