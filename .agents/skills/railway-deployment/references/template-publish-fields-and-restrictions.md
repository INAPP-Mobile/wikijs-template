# Template Publish Fields & Restrictions

**Field-level constraints for `templatePublish(id, input)`. Empirically verified 2026-07-08.**

## Field Constraints

### `description` — 75 char MAX

```graphql
input: { description: "Plausible CE - privacy-friendly web analytics" }   # 45 chars ✓
input: { description: "Privacy-friendly, cookie-free, self-hosted..." }    # 50 chars ✓
input: { description: "<anything over 75 chars>" }                         # ✗ Error: "Must be 75 or fewer characters long"
```

**Format that works** (verified across 3 existing reference templates):

| Template | Description | Length |
|----------|-------------|--------|
| `plausible-analytics-ce` | `Privacy-friendly, cookie-free, self-hosted web analytics` | 54 |
| `plausible` (254cc715) | `Open-source, privacy-friendly Google Analytics alternative` | 60 |
| `mzYEXO` (6d371192) | `Lightweight, open-source web analytics` | 39 |
| `plausible-ce` (55ebc0a2, our publish) | `Plausible CE - privacy-friendly web analytics` | 45 |

**Patterns that work:**
- Comma-separated adjectives + noun: `"Privacy-friendly, cookie-free, self-hosted web analytics"`
- Sentence with name + dash + description: `"Plausible CE - privacy-friendly web analytics"`
- Lead with key adjective: `"Lightweight, open-source web analytics"`

**Avoid:**
- Leading verb: ✗ `"Run Plausible CE on Railway..."` (no confirmed rejection but doesn't match reference style)
- More than 75 chars: ✗ hard error from the API
- All-caps abbreviations: ✗ `"Plausible CE - Privacy-Friendly Web Analytics"` (works but non-standard)
- Emojis / special characters: ✗ untested, likely rejected

### `category` — Must Be in Valid Enum

```graphql
input: { category: "Analytics" }     # ✓
input: { category: "AI/ML" }         # ✓
input: { category: "Other" }         # ✓ (catch-all)
input: { category: "Pl-analytics" }  # ✗ NOT a valid enum value
```

**Valid categories** (from `2026-06-29-railway-template-graphql-mutations.md`):
`AI/ML`, `Analytics`, `Authentication`, `Automation`, `Blogs`, `Bots`, `CMS`, `Observability`, `Other`, `Starters`, `Storage`, `Queues`

### `image` — Must Be a Direct SVG/PNG URL (Not HTML)

```graphql
input: { image: "https://raw.githubusercontent.com/owner/repo/main/template-icon.svg" }   # ✓
input: { image: "https://files.catbox.moe/4z7j3m.svg" }                                  # ✓
input: { image: "https://devicons.railway.app/i/clickhouse.svg" }                        # ✓
input: { image: "https://simpleicons.org/icons/plausibleanalytics.svg" }                 # ✗ Returns HTML, not SVG
```

**Working CDNs (verified 2026-07-08):**
- `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<file>.svg` — best for committed icons
- `https://files.catbox.moe/<hash>.svg` — for one-off icons
- `https://devicons.railway.app/i/<name>.svg` — for Railway-managed service icons

**Avoid:**
- `simpleicons.org/icons/...` — returns an HTML wrapper, not raw SVG
- `github.com/.../raw/...` (without `raw.githubusercontent.com`) — may serve HTML

### `readme` — Full Markdown, JSON-Escaped

```graphql
input: { readme: "# Deploy Plausible CE on Railway\n\n..." }   # Multi-line OK, must be JSON-escaped
```

**Max length:** No hard cap (verified up to 8,975 chars).

**Format:** Standard GitHub-flavored markdown. The dashboard renders the README on the template's marketplace page.

### `workspaceId` — Required

```graphql
input: { workspaceId: "b82233e8-ff27-4ca9-9a30-a7411337a2d9" }   # ✓ required
```

Get from any existing project: `query { project(id: "<PROJECT_ID>") { workspace { id } } }`

### `demoProjectId` — Optional

A public demo project. Skipped if you don't have one.

## The Critical Constraint: Already-Published Updates Are Flaky

**If the template is already in `PUBLISHED` state, calling `templatePublish` again does NOT reliably update all fields.**

Empirically verified 2026-07-08:

| Field | Update on re-publish? |
|-------|----------------------|
| `category` | Usually works |
| `image` | Sometimes works (worked on the 2nd attempt) |
| `description` | Inconsistent (worked once, failed silently once) |
| `readme` | **Often silently rejected.** Set to `null` or unchanged. |

**The only reliable way to update readme/description/image on an already-published template is the dashboard template editor:**

```
https://railway.com/workspace/templates/<template-id>
```

Open the template, click Edit, modify the fields, Save. The dashboard's UI gives clearer error messages than the API.

## Pattern: First Publish vs Update

```bash
# FIRST PUBLISH: include all fields (readme required)
mutation TemplatePublish($id: String!, $input: TemplatePublishInput!) {
  templatePublish(id: $id, input: $input) { id code status }
}
variables: {
  "id": "55ebc0a2-2378-45c5-a396-3b748046242f",
  "input": {
    "category": "Analytics",
    "description": "Plausible CE - privacy-friendly web analytics",
    "image": "https://files.catbox.moe/4z7j3m.svg",
    "readme": "<full markdown>",
    "workspaceId": "b82233e8-ff27-4ca9-9a30-a7411337a2d9"
  }
}

# RE-PUBLISH: include ONLY fields you want to change (readme may be ignored)
# Better: use the dashboard for readme/description/image updates
```

## Pre-Publish Checklist

Before calling `templatePublish`:

- [ ] `description` ≤ 75 chars, matches reference template format
- [ ] `category` is in the valid enum
- [ ] `image` URL serves raw SVG/PNG (test with `curl -I <url>` — should return `image/svg+xml` or `image/png`)
- [ ] `readme` is full markdown, JSON-escaped
- [ ] `workspaceId` is the target workspace's UUID
- [ ] `AGENTS.md` rules checked: sentence case display name, no text in icon, no auto-publish unless issues fixed
- [ ] Template is in DRAFT state, or you're OK with flaky readme/description updates

## Lesson: Newly-Published Templates May Not Appear in Marketplace Search

After the first `templatePublish` succeeds, the template may be **invisible in marketplace search results** for an indeterminate period (lag in the search index, or workspace-private unlisted state). The public URL `https://railway.com/deploy/<code>` still works (HTTP 200) and direct ID lookups succeed, but the template doesn't appear in the global `templates { edges { ... } }` listing.

**Verification path:** Always confirm the public URL returns 200, not just that the direct ID query shows `status: PUBLISHED`. If the template should be listed and isn't, wait a few minutes and re-query — or check whether the workspace settings have a "private" / "unlisted" toggle.

## Dashboard Path for Manual Updates

When the API fails or returns misleading errors on already-published templates, open:

```
https://railway.com/workspace/templates/<template-id>
```

The dashboard editor:
- Shows explicit error messages per field
- Persists readme/description/image reliably
- Lets you preview the marketplace page
- Is the ONLY way to update the template's display name (the `name` field) without deleting + recreating

## Related Files

- `railway-graphql-misleading-errors-and-verify-discipline.md` — companion ref for the API error patterns
- `railway-graphql-template-introspection.md` — `TemplatePublishInput` schema + introspection
- `2026-06-29-railway-template-graphql-mutations.md` — older mutation reference
- `2026-06-29-railway-graphql-template-readme-update.md` — earlier README update session
- `SKILL.md` § "Pitfall: Already-Published Templates Are Read-Only Via API"
