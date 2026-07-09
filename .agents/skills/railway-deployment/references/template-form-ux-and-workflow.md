---
type: reference
title: "Template Form UX and Publish Workflow"
---

# Template Form UX and Publish Workflow

## Key Lessons From Plausible CE Session

### 1. Never Publish Without Explicit Consent

User said multiple times: **"do not publish template until issues fixed"**, **"don't publish template without my consent"**.

**Rule:** Keep template **draft** (UNPUBLISHED) until user explicitly asks to publish. Draft = files ready, not live. User publishes from dashboard when ready.

### 2. Empty Form Fields Are Bad UX

The draft form showed empty textboxes with asterisks for Postgres plugin vars:
```
PGDATA * Value
POSTGRES_DB * Value
POSTGRES_USER * Value
POSTGRES_PASSWORD * Value
```

User said: **"Postgres plugin form, shouldn't be empty boxes, how should user know what to fill out?"**

**Resolution:** Remove the form entirely, not add labels. Plugin auto-injects all vars:
- User sees fewer form fields
- Plugin manages credentials dynamically
- No stale credential risk

**Rule:** If plugin form has empty/unlabeled vars → delete the form files, don't fill them. Plugin auto-injects work.

### 3. Draft Template = Created But Not Published

**`railway templates create` CLI requires the service to have a Docker image source.** If deployed via `railway up`, the CLI fails with "Service X does not have a source". Fall back to the Railway dashboard "Generate Template" action instead. See `references/templates-create-requires-image-source.md`.

CLI path (only works with image source):
```bash
railway templates create --project <project-id>
```

Dashboard path (always works):
1. Open project in Railway dashboard → "Generate Template"
2. Creates unpublished draft from any deployed project

To publish (only when user consents):
```bash
railway templates publish <code> --category "..." --description "..." --readme-file README.md
```

To unpublish (back to draft):
```bird
railway templates unpublish <code>
```

### 4. Original Project as Test Bed

User said: **"are you able to deploy THE template to new project?"** and **"try to deploy from draft template"**.

Draft templates only testable via `/new/template/<code>` if published. Drafts stay private.

**Workaround:** Test via the **original source project** (`railway status`, `railway up`, `railway logs --service <name>`). Files in git repo already mirror what the draft template uses.

### 5. Per-Service File Layout

```
plausible/
├── Dockerfile                      ← plausible-ce (main service)
├── template-vars.json              ← plausible-ce form (user fills if needed)
├── template-editor-raw.json        ← plausible-ce deploy form
├── clickhouse/
│   ├── Dockerfile                  ← clickhouse (companion service)
│   ├── template-vars.json          ← clickhouse form source
│   └── template-editor-raw.json    ← clickhouse deploy form
└── companion-mapping.json          ← glues clickhouse vars (NOT postgres plugin)
```

**Postgres plugin** = NO directory, NO JSON files. Lives in `railway.toml` under `[[services.plugins]]`. Railway injects vars automatically.

### 6. Display Rendering Bug With `&&` Files

When user asked `cat Dockerfile`, terminal collapsed `&&` characters made CMD look malformed. Had to use `od -c` to verify actual bytes.

**Rule:** Always verify with `od -c` or `python3 -c 