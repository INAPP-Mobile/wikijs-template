# Per-Service Form Structure

When a Railway template deploys multiple services, the file layout follows one rule:

**Each deployable service gets its own form. Plugin services get NO form.**

## Concrete Example: Plausible (3 services)

```
plausible/                          ← template root
├── Dockerfile                      ← plausible-ce service
├── template-vars.json              ← plausible-ce form source
├── template-editor-raw.json        ← plausible-ce deploy form (user fills)
├── clickhouse/
│   ├── Dockerfile                  ← clickhouse companion service
│   ├── template-vars.json          ← clickhouse form source
│   └── template-editor-raw.json    ← clickhouse deploy form (user fills)
└── companion-mapping.json          ← glues clickhouse vars into macros
```

**Postgres plugin** — no directory, no JSON files:
- Lives inside `railway.toml` under `[[services.plugins]]`
- Railway auto-injects `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `PGDATA` into the plausible-ce container at runtime
- NEVER add these to any `template-editor-raw.json` — user manages zero Postgres vars

## The companion-mapping.json Glue

Tells Railway "expose clickhouse vars so macros can reference them":

```json
{
  "clickhouse": {
    "CLICKHOUSE_USER": "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD", 
    "CLICKHOUSE_DB": "CLICKHOUSE_DB"
  }
}
```

This make `${{clickhouse.CLICKHOUSE_USER}}` work inside `template-vars.json` references. Without the mapping file, the deploy form sees clickhouse vars as opaque companion state.

## Rule Summary

| Service type | Form? | Where vars live |
|---|---|---|
| Dockerfile service (main) | YES — `template-editor-json` | User fills + auto-injected by plugin |
| Dockerfile companion (clickhouse) | YES — `clickhouse/template-editor-raw.json` | User fills + companion-mapping exposes them |
| Plugin (postgres, mysql, redis) | NO — Railway manages entirely | Auto-injected; NEVER re-export to form |

## Multi-Service Var Flow

```
User fills plausible-ce form:     BASE_URL, SECRET_KEY_BASE, DISABLE_REGISTRATION...
User fills clickhouse form:       CLICKHOUSE_DB, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD...
                                   ↓
companion-mapping.json exposes:   ${{clickhouse.CLICKHOUSE_USER}} etc.
                                   ↓
Plausible references:             CLICKHOUSE_DATABASE_URL uses those macros
                                   ↓
Postgres plugin auto-injects:     DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD...
into plausible-ce container       ↓
Plausible reads ALL env vars at runtime
```
