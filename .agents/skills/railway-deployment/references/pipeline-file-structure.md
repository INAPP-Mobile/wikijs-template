# Pipeline File Structure (v2.1)

```
scripts/pipeline/
├── __init__.py           # Orchestrator: arg parsing, prefix stripping, step dispatch
├── core.py               # Colors, prints, LLM call (call_worker), file helpers
├── step_0_research.py    # Static checks + dedup (5 retries)
├── step_1_dockerfile.py  # 4-phase LLM fix: USER → EXPOSE → HEALTHCHECK → verify
├── step_2_env_example.py # Deterministic .env parsing from Dockerfile ENV directives
├── step_3_icons_readme.py# Icons (deterministic) + README (LLM)
├── step_4_build_test.py  # Podman build, health check, LLM auto-fix on failure
├── step_5_commit_push.py # Git add/commit/push
├── step_6_deploy.py      # railway up
├── step_7_vars_template.py # template-vars.json + template-editor-raw.json
├── step_8_pre_publish.py # Pre-publish validation
├── step_9_publish.py     # Draft-only (no auto-publish to marketplace)
└── step_10_teardown.py   # Cleanup or keep
```

## Entry Point

```bash
python scripts/pipeline.py <app-name> [--start-step N] [--no-pause]
```

## Key Conventions

- **No railway- prefix**: `open-webui` not `railway-open-webui`
- **Small LLM prompts**: One action per call, not big prompts
- **Foreground execution**: Background processes get SIGTERM killed
- **Template updates only affect NEW deployments**
- **Volume in both files**: railway.json AND railway.toml
