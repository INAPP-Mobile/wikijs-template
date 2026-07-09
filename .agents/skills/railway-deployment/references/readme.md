# railway-deployment

_Umbrella skill for Railway template marketplace publishing — covers deploys, plugin services, and template publication._

## Files

| File | Purpose |
|------|---------|
| `references/plausible-crash-malformed-cmd.md` | Malformed CMD chains + display-rendering trap for `&&` characters (cat collapses display of `&&` between words — Python repr/raw bytes only valid verification method) |
| `references/stale-credentials-plugin-rotation.md` | Stale credentials after plugin-backed redeploy (Railway rotates passwords; hard-coded `DATABASE_URL` values immediately obsolete) |
| `references/railway-cli-non-interactive.md` | Non-interactive confirmation loops (pass `--yes` to leaf subcommands, not parents; pipe echoing responses still fails) |

See also sibling skills:
- `railway-template-publish` — end-to-end pipeline review
- `railway-template-variables` — `template-vars.json` / `template-editor-raw.json` schema


When future sessions touch similar territory — base-image entrypoint.sh behavior verification, plugin service interplay, publish confirmations — load relevant reference instead of pulling full SKILL.md.