# Random Template Codes — 2026-07-09

Date: 2026-07-09
Repo: INAPP-Mobile/railway-node-red
Template: `node-red-2` (old) → `spyQkl` (new)

## Problem

After deleting the old `node-red-2` draft and re-creating from a project renamed to `node-red`, Railway assigned a **random 6-character code** (`spyQkl`) to the new template. The project name did NOT influence the template code, despite existing references claiming it should.

This is a gap in the existing skill docs, which only cover the **"collision adds `-N` suffix"** case (see `2026-06-29-stirling-pdf-deploy-button-fix.md`) — not the **"random code generated from scratch"** case we hit.

## What the existing docs claim

| Reference | Claim |
|---|---|
| `2026-06-26-kanboard-qa-test.md` | "Railway derives the template slug from the **project name**, not the GitHub repo name." |
| `2026-06-29-railway-template-kanban-pipeline.md` | "Template slug — Derived from **project name** at `templates create` time, not repo name. Create project with desired slug name." |
| `2026-06-29-stirling-pdf-deploy-button-fix.md` | "the actual template code was `stirling-pdf-1` (the `-1` suffix was auto-generated because `stirling-pdf` was already taken)" — project name `stirling-pdf` → code `stirling-pdf-1` |

The kanban-pipeline docs even prescribe:
> "**Project rename check before publish** — The Publisher step now runs `railway project rename` if the project name doesn't match the intended template slug."

## What we actually observed

Workflow executed (2026-07-09, INAPP workspace):

1. Created test project `node-red-test` → `railway templates create` → got random code `gFTyNZ` ❌
2. Renamed project to `node-red` via GraphQL `projectUpdate` → deleted draft → recreated → got random code `spyQkl` ❌
3. Verified the rename: `railway status` showed `Project: node-red` ✓
4. No collision existed (the old `node-red-2` draft was deleted in step 2)
5. Result: 0/2 attempts produced a code derived from the project name

**Conclusion: the "rename project to desired slug" workflow documented in the kanban-pipeline is no longer reliable.** As of 2026-07-09, `railway templates create` can assign random 6-character codes regardless of the project name.

## Empirical data: INAPP workspace template codes (2026-07-09)

23 templates listed. **18 have human-readable codes** (likely manually set in dashboard at some point), **5 have random 6-char codes**:

| Code | Name | Status | Readable? | Likely derivation |
|---|---|---|:---:|---|
| `arcane` | arcane | PUBLISHED | ✓ | project name |
| `beszel` | beszel | PUBLISHED | ✓ | project name |
| `blinko` | blinko | PUBLISHED | ✓ | project name |
| `blocky` | blocky | PUBLISHED | ✓ | project name |
| `caddy-with-file-upload` | Caddy with file upload | PUBLISHED | ✓ | project name (normalized) |
| `changedetectionio-1` | changedetection.io | PUBLISHED | ✓ | project name + collision suffix |
| `content-playfulness` | CRUD API Builder | PUBLISHED | ❌ | **random** |
| `dragonfly-1` | dragonfly | PUBLISHED | ✓ | project name + collision suffix |
| `eary-form` | Easy Form | PUBLISHED | ⚠ | typo (custom) |
| `gotify` | gotify | PUBLISHED | ✓ | project name |
| `humble-illumination` | QR & Barcode Generator | PUBLISHED | ❌ | **random** |
| `html-to-markdown-converter` | HTML to markdown converter | PUBLISHED | ✓ | project name (normalized) |
| `kanboard-1` | kanboard | PUBLISHED | ✓ | project name + collision suffix |
| `keycloak-1` | keycloak | PUBLISHED | ✓ | project name + collision suffix |
| `og-image-template` | OG Image Generator | PUBLISHED | ✓ | custom (set in dashboard) |
| `open-webui-3` | open-webui | PUBLISHED | ✓ | project name + collision suffix |
| `plausible-ce-1` | Plausible CE | PUBLISHED | ✓ | project name + collision suffix |
| `pocketbase-5` | pocketbase | PUBLISHED | ✓ | project name + collision suffix |
| `railway-n8n` | n8n | PUBLISHED | ✓ | project name (with railway- prefix) |
| `railway-stirling-pdf` | Stirling PDF | PUBLISHED | ✓ | project name (with railway- prefix) |
| `railway-telegram-gateway` | Telegram Gateway | PUBLISHED | ✓ | project name (with railway- prefix) |
| `stirling-pdf-1` | Stirling PDF | PUBLISHED | ✓ | project name + collision suffix |
| `tududi-template-gi-1` | tududi | PUBLISHED | ✓ | custom (set in dashboard) |
| `filebrowser` | filebrowser | UNPUBLISHED | ✓ | project name |
| `homepage` | homepage | UNPUBLISHED | ✓ | project name |
| `memos-3` | memos | UNPUBLISHED | ✓ | project name + collision suffix |
| `netdata-1` | netdata | UNPUBLISHED | ✓ | project name + collision suffix |
| `railway-ghost` | ghost - abandoned... | UNPUBLISHED | ✓ | project name (with railway- prefix) |
| `railway-hoppscotch` | hoppscotch | UNPUBLISHED | ✓ | project name (with railway- prefix) |
| `spyQkl` | node-red | UNPUBLISHED | ❌ | **random (2026-07-09)** |
| `syncthing-1` | syncthing | UNPUBLISHED | ✓ | project name + collision suffix |
| `vaultwarden-3` | vaultwarden | UNPUBLISHED | ✓ | project name + collision suffix |
| `whoogle-search` | whoogle-search | UNPUBLISHED | ✓ | project name |
| `wikijs-template` | wikijs | UNPUBLISHED | ✓ | project name (with -template suffix) |

Random codes observed across the workspace: `content-playfulness`, `humble-illumination`, `gFTyNZ` (our 1st attempt), `spyQkl` (our 2nd attempt after rename). Pattern: random codes persist through PUBLISHED state (the first two), so **publishing does NOT auto-replace a random code** — the user's hypothesis on 2026-07-09 was incorrect.

## What you can do

1. **Accept the random code** (recommended for most cases):
   - Update the README's `[![Deploy on Railway](...)](https://railway.com/new/template/<code>)` button URL to use the actual code
   - Update the `> **Canonical code:**` callout to match
   - Commit + push the README change (verify remote per AGENTS.md rule 7)
   - The marketplace listing will use `railway.com/deploy/<code>` — works fine, just less memorable

2. **Manually set a custom code via the dashboard** (if human-readable URL matters):
   - Open `https://railway.com/workspace/templates/<template-id>`
   - Find the slug/code field in template settings
   - Set to desired value (e.g., `node-red-2`)
   - Update README to match
   - **No API/CLI path exists for this** (no `templateUpdate` mutation, no `--code` flag)

3. **Try the rename workflow ONE more time before accepting the random**:
   - Sometimes Railway does honor the project name. The kanban-pipeline docs still work for some workspaces. Worth a single attempt:
     ```bash
     railway project rename <desired-slug>     # if CLI supports
     # OR: GraphQL projectUpdate(id: "...", input: { name: "<desired-slug>" })
     railway templates delete <old-id> --yes
     railway templates create --project <id> --json
     railway templates list --json | jq '.[] | select(.name=="<slug>") | .code'
     ```
   - If you get a random code, fall back to option 1 or 2.

## What to update in the pipeline

- **Stirling PDF / broken-deploy-button-urls / template-audit-methodology** references all say "use the actual published code" — this is still correct, just incomplete. The new failure mode is "actual code is random, not derived from name."
- **Kanban-pipeline / kanboard-qa-test** references claim project name → slug derivation. This is **partially obsolete** as of 2026-07-09. Update the language to "may produce a code derived from the project name, or a random 6-character code" with the workaround.

## Related files

- `2026-06-26-kanboard-qa-test.md` — original "project name → slug" claim
- `2026-06-29-stirling-pdf-deploy-button-fix.md` — "collision adds suffix" case
- `2026-06-29-railway-template-kanban-pipeline.md` — the project-rename-then-create workflow
- `2026-06-29-broken-deploy-button-urls.md` — checklist requiring actual code
- `2026-07-02-template-audit-methodology.md` — "draft code differs from final code"
- `2026-06-29-railway-template-graphql-mutations.md` — no `templateUpdate` mutation
- `2026-06-29-service-vars-not-promoted-to-template-vars.md` — template vars are dashboard-only
- `2026-06-29-railway-template-graphql-queries.md` — `template(code:)` query

## Lesson

**Always verify the actual template code after `railway templates create`** — don't assume the project name will be honored. The README deploy button URL must use the actual code, not the desired slug, because the code can be either human-readable (project-name-derived, possibly with `-N` collision suffix) or a random 6-character string. There is no API/CLI path to change the code post-creation; the dashboard is the only override.
