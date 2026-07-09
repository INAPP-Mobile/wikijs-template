# Plugin Auto-Injected Variables vs. Deploy Form Variables

## The Three Layers

```
User fills form → Template vars become container env vars
Plugin auto-inject → Plugin vars become container env vars  
Docker container → Reads all env vars (form + plugin)
```

## Rule: Plugin Vars in Deploy Form

**DO NOT** put Railway plugin-managed variables in `template-editor-raw.json`
or `template-vars.json`:

- `DATABASE_URL` (Postgres/MySQL plugin)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `PGDATA`
- `CLICKHOUSE_DATABASE_URL` (when using companion-mapping)
- Any var Railway auto-injects from `[[services.plugins]]`

**Why:** Railway plugin already injects these at runtime. Putting them in
the deploy form creates stale literal strings that override the plugin's
dynamic values, causing `DATABASE_URL=` empty or wrong passwords.

## Companion Service Vars (Exception)

**DO** put companion service vars in `clickhouse/template-editor-raw.json`:

- `CLICKHOUSE_DB`
- `CLICKHOUSE_USER`  
- `CLICKHOUSE_PASSWORD`
- `PORT`

These are NOT plugin-auto-injected. The companion service owns them.

## companion-mapping.json Role

Maps plugin/template vars between services:

```json
{
  "postgres": {
    "DATABASE_URL": "DATABASE_URL"  // plugin injects → consumer reads
  },
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER"  // companion service vars
  }}
```

**This file NOT deploy form.** It tells Railway how wire services together.## Per-Service JSON Files

Separate deploy form each deployable service:

- `template-vars.json` + `template-editor-raw.json` → main service (plausible-ce)
- `clickhouse/template-vars.json` + `clickhouse/template-editor-raw.json` → companion servicePostgres plugin produces NO JSON files. Railway handles internally.
