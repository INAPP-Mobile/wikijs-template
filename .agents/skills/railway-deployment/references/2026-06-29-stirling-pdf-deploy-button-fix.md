# Stirling PDF Deploy Button Fix — 2026-06-29

## Problem

The published template `stirling-pdf-1` had a broken "Deploy on Railway" button in the README. The button URL was:

```
https://railway.app/template/stirling-pdf
```

But the actual template code was `stirling-pdf-1` (the `-1` suffix was auto-generated because `stirling-pdf` was already taken). Clicking the button led to a 404.

## Root Cause

The README deploy button used the desired slug (`stirling-pdf`) instead of the actual published template code (`stirling-pdf-1`).

## Fix Applied

1. Updated local README.md: changed both occurrences of `railway.app/template/stirling-pdf` to `railway.app/template/stirling-pdf-1`
2. Pushed to GitHub (`INAPP-Mobile/railway-stirling-pdf@39f9f73`)
3. Railway template still needs update with the corrected README (blocked on auth)

## GraphQL Mutation for Template Update

```graphql
mutation TemplatePublish($id: String!, $input: TemplatePublishInput!) {
  templatePublish(id: $id, input: $input) {
    id
    code
    name
    readme
    image
  }
}
```

**Variables:**
```json
{
  "id": "dce8dc2c-5b88-4a84-8fe5-c4f1dad58ddb",
  "input": {
    "category": "Other",
    "description": "Self-hosted PDF tool with 50+ tools, zero dependencies, 84K★.",
    "image": "https://raw.githubusercontent.com/INAPP-Mobile/railway-stirling-pdf/main/template-icon.svg",
    "readme": "<FULL_README_CONTENT_ESCAPED>",
    "workspaceId": "b82233e8-ff27-4ca9-9a30-a7411337a2d9"
  }
}
```

**Endpoint:** `https://backboard.railway.com/graphql/v2`
**Auth:** `Authorization: Bearer <Account_Token>` (format: `railway_...`)

## Template Publish Input Type

```
input TemplatePublishInput {
  category: String
  demoProjectId: String
  description: String
  image: String
  readme: String
  workspaceId: String
}
```

## Lesson

Always verify the actual template code from `railway templates list --json` or the `templates create` output, and use that exact code in the deploy button URL. The desired name and the published code can differ.