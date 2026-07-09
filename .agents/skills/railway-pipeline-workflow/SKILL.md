---
name: railway-pipeline-workflow
description: "Run Python-driven Railway template pipeline with small LLM phases. Dedup, build-test, draft-only publish. No auto-prefix overhead."
tags: [railway, pipeline, workflow, llm]
---

# Railway Pipeline Workflow

How to run the Python-driven template pipeline end-to-end.

## Quick Start

```bash
cd /var/home/ihshim523/Work/railway
python scripts/pipeline.py <app-name> --start-step 0
```

## Key Rules

1. **No `railway-` prefix** on project dirs
2. **Pipeline never auto-publishes** — step 9 = draft only
3. **Small LLM prompts** > big ones (prevents 300s+ timeouts)
4. **Dedup first** — substring match both directions catches `open-webui` vs `open-webui-3`

## Step Phases Reference

See `railway-deployment` skill for full architecture.

## Worker Hang Fix

```python
env = os.environ.copy()
env["TERM"] = "dumb"
subprocess.run(
    ["worker", "-z", prompt],
    env=env, stdin=subprocess.DEVNULL, timeout=600
)
```

**BOTH** `TERM=dumb` AND `stdin=subprocess.DEVNULL` required. `TERM=dumb` prevents `tcsetattr: Inappropriate ioctl device` (worker tries setting terminal mode). `stdin=subprocess.DEVNULL` prevents `tcsetpgrp` hang on background processes.

## After Pipeline

User must manually publish:
```bash
railway templates publish <code> --category "AI/ML" --description "..." --readme-file README.md
```
