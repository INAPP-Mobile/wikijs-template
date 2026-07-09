# Railway Template Pipeline: Three-Layer Orchestration Architecture

**Date:** 2026-06-29
**Context:** Refactored dispatch scripts to separate concerns between Gateway Dispatcher, queue logic, and gatekeeper/pre-flight checks.

## The Three Layers

```
┌─────────────────────────────────────────────────────────�
│ Layer 1: Gateway Dispatcher (Hermes Kanban built-in)     │
│   - Polls for `ready` tasks every 60s                     │
│   - Spawns worker processes                               │
│   - Handles claim/lock/lifecycle, retries, timeouts      │
│   - Should NOT be disabled — it handles agent execution  │
├─────────────────────────────────────────────────────────┤
│ Layer 2: DAG / Chain Reaction (create-next-card.sh)      │
│   - Each agent creates the next card on completion        │
│   - RAW body forwarding (agent can't strip FIRST ACTION)  │
│   - Contains ALL pre-flight: token sync + concurrency     │
│   - Single chokepoint every agent calls                   │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Queue Gatekeeper (dispatch-queue.sh)            │
│   - Decides WHEN to start the next template               │
│   - Tracks queue state (template-queue.json)              │
│   - Idle-checks the board before dispatching              │
│   - Runs via systemd timer (every 2 min)                  │
└─────────────────────────────────────────────────────────┘
```

## What Lives Where

| Concern | Location | Why |
|---------|----------|-----|
| Token sync (v5.23 fix) | `create-next-card.sh` | Every agent calls this — single chokepoint |
| Concurrency guard (lock) | `create-next-card.sh` | Prevents parallel pipelines at the chokepoint |
| Card creation logic | `create-next-card.sh` | RAW body forwarding, dedup, priority inheritance |
| Queue advancement | `pub-body.txt` (agent) | Publisher marks done, increments index |
| Idle-check + dispatch | `dispatch-queue.sh` | Systemd timer triggers when board is idle |
| Agent lifecycle | Gateway Dispatcher | Built-in, don't disable |
| One-off dispatch | `dispatch-pipeline.sh` | Thin wrapper, creates root card only |

## Concurrency Guard Pattern

```bash
# In create-next-card.sh (single chokepoint):
LOCK_FILE="$PROJECT_DIR/pipeline-locks/.pipeline.lock"
if [ -f "$LOCK_FILE" ]; then
  LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
    echo "Skipped - another pipeline is active (PID $LOCK_PID)."
    exit 0  # Clean exit, agent knows not to retry
  else
    rm -f "$LOCK_FILE"  # Stale lock
  fi
fi
echo $$ > "$LOCK_FILE"
trap "rm -f '$LOCK_FILE'" EXIT
```

Key design decisions:
- Lock file is in `pipeline-locks/` (not `pipeline-locks/` — the latter is for output reports)
- `kill -0` checks PID liveness (handles stale locks from crashed agents)
- `trap` ensures cleanup on exit (even on error)
- Exit 0 (not 1) on lock contention — agent shouldn't fail, just skip

## dispatch-queue.sh as systemd Timer

```ini
# ~/.config/systemd/user/railway-dispatch.timer
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
AccuracySec=30s
```

```ini
# ~/.config/systemd/user/railway-dispatch.service
[Service]
Type=oneshot
ExecStart=/var/home/ihshim523/Work/railway/scripts/dispatch-queue.sh
WorkingDirectory=/var/home/ihshim523/Work/railway
```

Enable: `systemctl --user enable --now railway-dispatch.timer`

The script:
1. Reads `template-queue.json` → finds next pending template
2. Checks `hermes kanban list --status running` → exits if busy
3. Archives done tasks → cleans board
4. Creates Research card for next template
5. Repeats every 2 min via timer dispatch → queue advances automatically

## dispatch-pipeline.sh — Thin Wrapper

After refactoring, this is minimal:
```bash
#!/usr/bin/env bash
set -euo pipefail
export HERMES_KANBAN_BOARD=railway-template
BODIES="...pipeline-bodies"
LOCK_FILE="...pipeline-locks/.pipeline.lock"

# Concurrency guard (redundant safety — create-next-card.sh also guards)
[ -f "$LOCK_FILE" ] && { /* check PID */ }

# Create root card
hermes kanban create --assignee worker3 \
  --body "$(cat "$BODIES/research-body.txt")" \
  "Research v1: Trending Railway Templates"
```

Token sync is NOT here — it's in `create-next-card.sh` where it runs on every card creation.

## Pitfall: Tool Content Stripping

`write_file` and `patch` tools strip certain sequences (confirmed again 2026-06-29):
- `railway whoami` can become garbled
- `LOCK_PID=$(cat ...)` can become `LOCK_PID=`
- Shell variable assignments with `$()` often mangle

**Reliable workaround:** Use `terminal` with heredoc:
```bash
cat > /path/to/script.sh << 'EOF'
#!/bin/bash
TOKEN_CHECK=*** whoami 2>&1)
LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
EOF
```

The outer single-quoted EOF delimiter prevents shell expansion. This works reliably.

## Related References

- `references/2026-06-29-template-queue-system.md` — Queue file format and Publication agent integration
- `references/2026-06-29-service-vs-template-variables.md` — Template vars (manual) vs service vars (CLI)
- `references/2026-06-29-railway-cli-token-field-mismatch.md` — v5.23 token sync details
- `references/2026-06-29-template-variable-config-dashboard.md` — Dashboard-only template variable config
