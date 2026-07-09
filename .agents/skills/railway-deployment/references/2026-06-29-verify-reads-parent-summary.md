# Verify Tasks Must Read Parent Completion Summary

## Problem

The Dev-3 (Verify) task body previously just listed what the previous agent "should have" done:
- Created template-icon.svg, og-image.svg
- Written README.md
- All files committed and pushed

This forced the verify worker to re-check everything from scratch or guess what was actually built.

## Solution

Add a pre-requisite step that instructs the verify worker to read the parent task's `kanban_complete` event:

```markdown
## Pre-requisite
Before doing anything else, read the parent task's completion summary to understand what the previous agent actually did:

\```bash
hermes kanban show <parent-task-id>
\```

Look for the `kanban_complete` event in the events list — it contains the Dev-2 agent's summary of what was built, what files were created, and any issues encountered. Use this as your ground truth instead of re-checking everything from scratch.
```

## Why This Matters

- The parent's `kanban_complete` summary is the authoritative record of what was done
- Without it, the verify worker wastes time re-discovering file lists, build issues, etc.
- The verify worker can focus on validation (build, run, health check) rather than archaeology

## Applied To

- `/var/home/ihshim523/Work/railway/pipeline-bodies/dev-verify.txt` — updated 2026-06-29
