# Template Queue System → Replaced by Single-Winner `winner.json`

**Date:** 2026-06-29 (original), 2026-06-29 (final)

> **⚠️ SUPERSEDED:** The multi-template queue (`template-queue.json` + `dispatch-queue.sh`) was replaced by `winner.json` + `dispatch.sh` on 2026-06-29. The pipeline picks ONE winner and ships it — no queue, no cursor, no post-publish handoff. See SKILL.md § "Single-Template Dispatch".

## Why the queue was removed

The pipeline's sole goal is to pick ONE template and ship it end-to-end. The ranked queue of loser candidates, `current_index` cursor, and post-publication "start next template" handoff were dead code — the pipeline never processes a second template.

## Migration steps (completed 2026-06-29)

| What changed | Details |
|---|---|
| `winner.json` | QA Gate v3 writes a single flat JSON: `{"name":"...", "category":"...", "repo":"...", "selected_at":"..."}` |
| `dispatch.sh` | Replaced `dispatch-queue.sh`. Reads `winner.json`, dispatches Research for the one winner. No index tracking. |
| `dispatch-queue.sh` | Deleted |
| `template-queue.json` | All references removed from goal.md, guide.md, pub-body.txt, deploy-publish.txt |
| `pub-body.txt` | Removed "Update Template Queue" and "Auto-Dispatch Next Template" sections |
| Systemd service | `railway-dispatch.service` ExecStart updated to `dispatch.sh`, description updated, `daemon-reload` run |
| "How to Finish" | All body files simplified: no `kanban_complete`, just "stop — dispatcher detects completion" |

## GraphQL API confirmation (template variables cannot be automated)

GraphQL introspection at `https://backboard.railway.com/graphql/v2` (2026-06-29, valid session token) confirmed:

**Available template mutations:**
- `templateClone`, `templateDelete`, `templateDeployV2`, `templateGenerate`, `templatePublish`, `templateUnpublish`, `templateVolumeUpdate`
- None accept variable configuration inputs

**Available variable mutations (service/env-level ONLY):**
- `variableUpsert` — `projectId!`, `environmentId!`, `name!`, `value!`, `serviceId?`, `skipDeploys?`
- `variableCollectionUpsert` — `projectId!`, `environmentId!`, `variables!`, `replace?`, `serviceId?`, `skipDeploys?`
- These set runtime env vars on deployed services, NOT template draft variables

**Template type inspection:**
- `Template.services → TemplateService.config` is an opaque scalar (JSON blob)
- `TemplatePublishInput` accepts: `category`, `description`, `image`, `readme`, `workspaceId`, `demoProjectId` — no variables field
- `TemplateGenerateInput` accepts: `projectId`, `environmentId` — no variables field

**Conclusion:** Template variable configuration (descriptions, required/optional, defaults, secret() functions) is dashboard-only. No CLI command, no GraphQL mutation, no automation possible. Browser tool fallback is the only option for programmatic pipelines.
