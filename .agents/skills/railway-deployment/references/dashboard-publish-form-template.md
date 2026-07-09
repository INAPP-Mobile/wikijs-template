# Dashboard Publish Form — Required Structure & Validator Rules

**Empirically verified 2026-07-09 (Keycloak template publish).** When you manually publish via the Railway dashboard editor (or paste the description via Raw JSON), the form has a strict validator that rejects drafts missing specific sections.

## Quick summary

- The form template REQUIRES specific H1/H2/H3 sections to be present in the description field
- App-name in section headings is LOWERCASE (this is a deliberate exception to `AGENTS.md` rule 2 — sentence case applies to display names elsewhere, but the dashboard form template literally uses lowercase `<appname>` in every heading and the validator rejected capitalized variants during the Keycloak publish on 2026-07-09)
- The section `Why Deploy <appname> on Railway?` is REQUIRED with a specific boilerplate
- `description` (short tagline) has a 75-char MAX limit
- `category` must be a valid enum value (see `template-publish-fields-and-restrictions.md`)
- `image` must serve raw SVG/PNG (no HTML, no simpleicons.org)
- If the workspace is blocked, you'll see "You have been blocked from publishing templates" regardless of template state

**Diagnostic tip:** Paste just the headings-only version of your description first to confirm the validator accepts the structure BEFORE filling the body. Saves round-trips when the section headings are wrong.

## The exact form template

The Railway dashboard's description field uses this exact template (placeholders in `[brackets]`):

```markdown
# Deploy and Host <appname> on Railway

[<50-word description of what <appname> is>]

## About Hosting <appname>

[<100-word description of what's involved in hosting>]

## Common Use Cases

- [Use case 1]
- [Use case 2]
- [Use case 3]

## Dependencies for <appname> Hosting

- [Dependency 1]
- [Dependency 2]

### Deployment Dependencies

[<external links relevant to the template>]

### Implementation Details <OPTIONAL>

[Code snippets or implementation details. Optional — exclude if nothing to add.]

## Why Deploy <appname> on Railway?

<!-- Recommended: Keep this section as shown below -->
Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying <appname> on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
<!-- End recommended section -->
```

## Critical: `<appname>` MUST be LOWERCASE in all section headings

Even though `AGENTS.md` rule 2 prefers sentence case (`Keycloak` not `keycloak`) for display names everywhere else, the dashboard form template's literal headings use lowercase `<appname>`. The validator rejects drafts when a required heading is missing or has unexpected casing — verified empirically on 2026-07-09 when `Why Deploy Keycloak on Railway?` (capital "Keycloak") was rejected with `Missing required sections: ## Why Deploy`, and switching to `Why Deploy keycloak on Railway?` (lowercase) was accepted.

The exact substrings the validator looks for:

- `## Common Use Cases` (no app name — works regardless of case)
- `## About Hosting <appname>` — validator greps for `About Hosting`
- `## Dependencies for <appname> Hosting` — validator greps for `Dependencies`
- `## Why Deploy <appname> on Railway?` — validator greps for `Why Deploy`

**Symptom of mismatch:** the form shows the error `Missing required sections: ## <header>` (code-fence the exact error if reporting in a ticket):

```
Missing required sections: ## Why Deploy
```

**Recommended fix:** lowercase the app name in ALL section headings, even if the body text uses sentence case. The body text is unaffected.

## Required sections checklist

Before clicking publish on the dashboard, confirm:

- [ ] H1: `# Deploy and Host <appname> on Railway` (lowercase appname)
- [ ] 50-word description immediately after H1 (replaces `[What is X?]` placeholder)
- [ ] `## About Hosting <appname>` with 100-word body
- [ ] `## Common Use Cases` with 3 list items (each `- [...]` replaced with `- <text>`)
- [ ] `## Dependencies for <appname> Hosting` with 2 list items
- [ ] `### Deployment Dependencies` with at least one link OR an explicit "No external links" note
- [ ] `### Implementation Details <OPTIONAL>` — can be omitted entirely if no implementation notes, OR kept with content
- [ ] `## Why Deploy <appname> on Railway?` with the EXACT boilerplate (or close variant)

## The "## Why Deploy" boilerplate is REQUIRED

The validation explicitly calls out `Missing required sections: ## Why Deploy` when this section is missing. The body of this section should match the Railway-recommended text (or be a very close variant that still keeps the core messaging). Verified boilerplate from the form:

```markdown
Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying <appname> on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
```

**Why this matters:** Railway's marketplace listings are SEO-heavy and the boilerplate is what gets indexed. Using the exact text (or close variant) keeps the listing consistent with the marketplace tone.

## Common validator rejections

| Error from the form | Cause | Fix |
|---|---|---|
| `Missing required sections: ## Why Deploy` | Section missing or capitalized differently | Add `## Why Deploy <appname> on Railway?` with lowercase appname |
| `Missing required sections: ## About Hosting` | Section missing | Add it with the description in the body |
| `Missing required sections: ## Common Use Cases` | Section missing or no list items | Add `## Common Use Cases` followed by 3 `- <text>` lines |
| `Missing required sections: ## Dependencies` | Section missing | Add `## Dependencies for <appname> Hosting` |
| `description: Must be 75 or fewer characters long` | Short description exceeds 75 chars | Trim to <= 75 chars (see `template-publish-fields-and-restrictions.md`) |
| `category: invalid value` | Not in enum | Use one of: AI/ML, Analytics, Authentication, Automation, Blogs, Bots, CMS, Observability, Other, Starters, Storage, Queues |
| `image: must be a valid URL serving SVG or PNG` | URL returns HTML or 404 | Use raw.githubusercontent.com or devicons.railway.app CDN |
| `You have been blocked from publishing templates` | **Workspace-level block, not template-level** | See "Workspace Block" section below |

## Workspace Block (the truly blocking error)

If the dashboard shows `You have been blocked from publishing templates` on EVERY publish attempt, this is a **workspace-level restriction** — not specific to your template. Railway has flagged your workspace (the `INAPP-Mobile` workspace in our case) and no template from it can be published until the team clears the block.

**What does NOT work:**
- Retrying the publish via dashboard → same error
- Retrying via GraphQL `templatePublish` → returns `INTERNAL_SERVER_ERROR` with the same message
- Retrying via CLI (`railway templates publish`) → same error
- Changing the template's category, description, or icon → still blocked

**What DOES work (as of 2026-07-09):**
- Open a support ticket at <https://station.railway.com> in the `Platform / Templates & Marketplace` category
- Railway does **NOT** handle this kind of issue over email — auto-responses from `team@railway.app` and other addresses redirect all general inquiries to station.railway.com, so retrying via email gets nowhere
- Title: `Workspace blocked from publishing templates`
- Body: explain which workspace (`INAPP-Mobile` in our case), mention the exact error message, include your template code so they can find it
- Once the team lifts the block, the publish command from the dashboard (or via GraphQL) will succeed on the FIRST retry

**Diagnostic to confirm it's a workspace block vs a template error:**
- Try publishing a DIFFERENT draft from the same workspace — if both fail with the same error, it's a workspace block
- Try publishing a draft from a DIFFERENT workspace — if it succeeds, definitely a workspace block on the first workspace
- The error text uses "publishing templates" (plural, generic) vs "publishing this template" (singular, specific) — the former implies workspace-level

## Re-publishing after the first publish

Per `template-publish-fields-and-restrictions.md` § "Already-Published Templates Are Read-Only Via API":

- `category` updates via re-publish: usually work
- `image` updates via re-publish: sometimes work (worked on 2nd attempt)
- `description` updates via re-publish: inconsistent
- `readme` updates via re-publish: **often silently rejected**

**For updates after the first publish, use the dashboard form editor** — not the API. The dashboard gives clearer per-field error messages and persists changes reliably (except for `readme`, which may still fail silently and require the dashboard text editor rather than Raw JSON paste).

## Quick reference: what to fill in the dashboard publish form

For a template named `<appname>` with stack features `[feature1, feature2]`:

| Field | Value |
|---|---|
| Short description | `<appname> with feature1 + feature2 on Railway` (≤75 chars) |
| Category | Pick from enum — match the closest fit |
| Icon URL | `https://raw.githubusercontent.com/<owner>/<repo>/<commit-sha>/template-icon.svg` (pin to commit, not `main`) |
| Overview H1 | `# Deploy and Host <appname> on Railway` |
| 50-word description | One paragraph explaining what the app does |
| `## About Hosting <appname>` | 100-word paragraph on what's involved in deploying |
| `## Common Use Cases` | 3 bullet points |
| `## Dependencies for <appname> Hosting` | 2 bullet points |
| `### Deployment Dependencies` | External docs/links |
| `### Implementation Details <OPTIONAL>` | Optional snippet or omit |
| `## Why Deploy <appname> on Railway?` | Exact boilerplate (or close variant) |

## Related files

- `template-publish-fields-and-restrictions.md` — companion reference for the GRAPHQL `templatePublish` mutation (category enum, description limit, image URL rules)
- `railway-graphql-misleading-errors-and-verify-discipline.md` — verify-after-mutate discipline for the GraphQL API
- `template-form-ux-and-workflow.md` — overall draft/publish/UX workflow
- `AGENTS.md` rule 2 — note that rule 2 (sentence case display name) DOES NOT apply to the dashboard form headings (lowercase required)
