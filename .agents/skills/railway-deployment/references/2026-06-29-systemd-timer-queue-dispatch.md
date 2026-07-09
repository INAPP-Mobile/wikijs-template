# Systemd User Timer for Queue Dispatch (2026-06-29)

When `crontab` is unavailable (e.g., Fedora Silverblue/Atomic, minimal containers, locked-down environments), use systemd user timers instead to schedule recurring queue dispatch.

## Why

- `crontab` is not installed on Fedora Silverblue/Atomic spins (confirmed: `which crontab` → not found)
- Even where installed, crontab is often disabled/blocked in production
- Systemd user timers work without root, survive reboots, and integrate with journal logging

## Pattern

### 1. Create service unit

`~/.config/systemd/user/<name>-dispatch.service`:
```ini
[Unit]
Description=Railway Template Queue Dispatcher
After=network-online.target

[Service]
Type=oneshot
ExecStart=/home/user/Work/railway/scripts/dispatch-queue.sh
WorkingDirectory=/home/user/Work/railway
Environment=HERMES_KANBAN_BOARD=railway-template
```

### 2. Create timer unit

`~/.config/systemd/user/<name>-dispatch.timer`:
```ini
[Unit]
Description=Run Railway Queue Dispatcher every 2 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
AccuracySec=30s

[Install]
WantedBy=timers.target
```

### 3. Enable and start

```bash
systemctl --user daemon-reload
systemctl --user enable --now railway-dispatch.timer
```

### 4. Monitor

```bash
# Check timer status
systemctl --user status railway-dispatch.timer

# View execution logs
journalctl --user -u railway-dispatch.service -f

# List all timers
systemctl --user list-timers
```

## Key Parameters

| Parameter | Effect |
|-----------|--------|
| `OnBootSec=2min` | Wait 2 min after boot before first run (lets gateway warm up) |
| `OnUnitActiveSec=2min` | Fire 2 minutes after each execution completes (not a fixed cron slot) |
| `AccuracySec=30s` | Coalesce wakeups within 30s window (saves power) |
| `Type=oneshot` | Service is "fire and forget" — not a daemon |

## Queue Agent Pattern

The service script (`dispatch-queue.sh`) should:
1. Check `hermes kanban list --status running` — skip if busy
2. Read `pipeline-logs/template-queue.json` for next item
3. `hermes kanban create` root Research card
4. Let built-in dispatcher + chain-reaction pattern handle the rest

## Pitfalls

- **Need log to file explicitly**: systemd captures stdout/stderr to journal, but for cron-style append logs add a redirect: `ExecStart=/path/to/script.sh >> /path/to/cron.log 2>&1`
- **User sessions linger**: systemd user services persist across logins. If the machine reboots, auto-start kicks in via the `[Install]` section.
- **Environment isolation**: User services don't inherit terminal env vars. Set all needed vars in the `[Service]` section.
