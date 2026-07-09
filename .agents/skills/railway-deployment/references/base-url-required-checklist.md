# Post-Publish Fresh Deploy Verification

After every template publish/update, **always deploy a brand-new project** from the published template. Never reuse the source project to verify — the source project manually gets injected overrides that hide template bugs.

## Fresh Deploy Checklist

Run inside a freshly-linked new project:

```bash
railway variables --service <app-service> --kv | grep DATABASE_URL
```

- `DATABASE_URL=` → **FAIL** (plugin companion var not resolving)
- `DATABASE_URL=postgresql://...@host:5432/db` → PASS

```bash
railway status
```

All services must show `Online`. Any `Crashed` is a template bug.

```bash
railway logs --service <app-service> --tail 10
```

Look for:
- `FATAL 28P01 invalid_password` → stale credentials baked into template
- `BASE_URL configuration option required` → empty BASE_URL default
- `PGDATA variable not start with expected volume mount path` → PGDATA conflict (don't put PGDATA in template-vars.json)

## Anti-Pattern: Source Project Smear

The source project used to develop the template has manual overrides: hardcoded passwords, manually-set BASE_URL, etc. Reusing it for verification passes only because of those overrides. Fresh projects get only what the template says — so bugs surface.

## User Correction Pattern (from this session)

User repeatedly hit "DATABASE_URL empty" / "BASE_URL required" loops. Investigation revealed:
- Template had no BASE_URL default (empty default)
- PGDATA was added to template conflicts with plugin-injected PGDATA
- Each publish captured stale password, then next deploy had empty/wrong creds

Template redesign that resolved everything:
- `BASE_URL = ${{RAILWAY_PUBLIC_DOMAIN}}` (auto-populated, never empty)
- Remove PGDATA entirely (plugin-managed)
- `DATABASE_URL = ${{Postgres.DATABASE_URL}}` (live at deploy time)
- Companion service vars `CLICKHOUSE_*` templated, not hardcoded

## One-Page Decision Matrix

| Error in fresh deploy | Root cause | Fix |
|---|---|---|
| `DATABASE_URL=` empty | Template missing `${{Postgres.DATABASE_URL}}` or duplicate Postgres services | Add macro; delete duplicate service |
| `FATAL 28P01` | Template baked stale password | Always `${{Postgres.DATABASE_URL}}` |
| `BASE_URL configuration option required` | Empty BASE_URL default | Set `${{RAILWAY_PUBLIC_DOMAIN}}` |
| `PGDATA variable not start` | Template PGDATA conflicts with plugin | Remove PGDATA from template entirely |
| `invalid URL ... no database name` | Missing `${{clickhouse.CLICKHOUSE_DB}}` | Add CLICKHOUSE_DB to companion service vars |

## Why Not Set PGDATA in Template?

Railway's Postgres plugin sets `PGDATA` to `/var/lib/postgresql/data` (no `/pgdata` suffix) fresh deploys. Adding `PGDATA=/var/lib/postgresql/data/pgdata` template conflicts plugin's own value at runtime, Postgres container crashes first-boot. Rule: never include plugin-managed vars in template-vars.json.
