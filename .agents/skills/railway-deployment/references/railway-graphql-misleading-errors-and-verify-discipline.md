# Railway GraphQL API: Misleading Errors & Verify Discipline

**LESSON LEARNED 2026-07-08 from Plausible CE session. READ THIS BEFORE ANY templatePublish / templateUnpublish / projectDelete / variableUpsert CALL.**

## The Problem: Error Messages Are Not Actionable

Railway's GraphQL API wraps many real errors (auth, scope, validation, internal server error) inside one of two misleading response shapes:

| Error | HTTP | What it actually means |
|-------|------|------------------------|
| `"Not Authorized"` (no `errorExtensions.code`) | 500 INTERNAL_SERVER_ERROR | Anything. Auth failure, scope failure, internal error, or **the mutation took effect anyway**. |
| `"Problem processing request"` | 500 INTERNAL_SERVER_ERROR | Anything. Same. |

**You cannot tell from the error message which one happened.** The mutation may have succeeded, partially succeeded, or genuinely failed — the response shape is the same.

## Affected Mutations (Empirically Verified 2026-07-08)

| Mutation | Symptom | Real outcome |
|----------|---------|--------------|
| `templatePublish(id, input)` (first call) | `"Not Authorized"` + 500 | **Mutation took effect** (template went PUBLISHED, code `plausible-ce` was assigned, marketplace URL returned 200). |
| `templatePublish(id, input)` (re-publish to already-published) | `"Not Authorized"` or `"Problem processing request"` | **Flaky.** Some updates (image) take, others (readme) don't. Description updates vary. |
| `templateUnpublish(id)` | `"Not Authorized"` + 500 | Genuinely did not unpublish. State remained `PUBLISHED`. |
| `projectDelete(id)` (production project) | `"Not Authorized"` + 500 | Genuine failure. Project verifiably still present after 3s. |
| `variableUpsert(input)` | `"Problem processing request"` + 500 | Often does not take effect. Use CLI `railway variable set` instead. |
| `serviceInstanceUpdate(serviceId, input)` (pre-existing pitfall) | Returns `true` silently | **May return true without persisting** changes across redeploys. See `SKILL.md` § "Pitfall: `serviceInstanceUpdate` Returns `true` But Doesn't Persist". |

**Rule of thumb:** If you get `"Not Authorized"` or `"Problem processing request"` from a Railway GraphQL mutation, **NEVER trust the response**. Run a separate read query and compare state.

## The Verify-After-Mutate Discipline

After every Railway GraphQL mutation, immediately run a separate read query and compare:

```bash
# 1. Run mutation
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"mutation($id: String!) { templatePublish(id: $id, input: $input) {...} }","variables":{...}}'

# 2. IMMEDIATELY run a separate read query (don't trust the mutation response)
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"query($id: String!) { template(id: $id) { id code status description image readme } }","variables":{"id":"<TEMPLATE_ID>"}}'
```

**Compare fields explicitly.** Don't rely on the mutation's return value — query the canonical state.

### State Comparison Bash Helper

```bash
verify_template() {
  local tid="$1"
  curl -s -X POST https://backboard.railway.app/graphql/v2 \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"query\":\"query(\$id: String!) { template(id: \$id) { code status description readme image } }\",\"variables\":{\"id\":\"$tid\"}}"
}

# After mutation:
ACTUAL=$(verify_template 55ebc0a2-2378-45c5-a396-3b748046242f)
echo "$ACTUAL" | python3 -c "import json,sys; t=json.load(sys.stdin)['data']['template']; print(f'code={t[\"code\"]} status={t[\"status\"]} desc={t[\"description\"]!r} readme_len={len(t[\"readme\"] or \"\")}')"
```

## When to Give Up on the API

For these operations, the API is genuinely unreliable — use the dashboard instead:

| Operation | API status | Fallback |
|-----------|-----------|----------|
| Update `readme` on already-published template | Flaky, often silently rejected | Dashboard template editor |
| Update `description` on already-published template | Inconsistent (sometimes works, sometimes not) | Dashboard template editor |
| Unpublish a published template | Returns 500, may not take effect | Dashboard template editor |
| Delete production project | Returns 500, may not take effect | Dashboard project settings |
| Update variable that contains a literal (non-`${{...}}`) value | Often stripped | `railway variable set` CLI on the source project + re-generate template |

**Dashboard template editor URL pattern:**
```
https://railway.com/workspace/templates/<template-id>
```

## Token Issues (Often the Real Cause)

The `"Not Authorized"` error is sometimes a **real auth failure** masked by the same response shape. Check these first:

| Check | How |
|-------|-----|
| Token expired | Compare with `~/.railway/api-token`; regenerate from `https://railway.com/account/tokens` |
| Wrong token type | `templatePublish` requires **Account Token** (`railway_...` prefix), NOT the session token from `~/.railway/config.json` |
| Wrong workspace ID | `templatePublish` input requires `workspaceId` matching the token's owner |
| Template owned by different workspace | Cross-workspace updates may fail silently |

**Always test the token on a read query first** to rule out auth issues before blaming the mutation:

```bash
# Token sanity check (should always work for any valid token)
curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ me { id email } }"}'
```

If this returns `me: null` or an error, the token is bad — don't waste time debugging the mutation.

## Decision Flowchart

```
Run mutation
  ↓
Got "Not Authorized" or "Problem processing request"?
  ↓ yes
Run separate read query
  ↓
Did state actually change?
  ↓ yes → Mutation worked. Treat as success despite error.
  ↓ no  → Mutation failed. Try:
           1. Re-run with explicit field (readme vs description vs image)
           2. Re-run after `sleep 2` (rate limit?)
           3. Use dashboard for readme/description on already-published templates
           4. Use CLI `railway variable set` instead of `variableUpsert`
           5. Escalate: dashboard or Railway support
```

## Real Examples From 2026-07-08 Session

### Example 1: `templatePublish` First Call Succeeded Despite "Not Authorized"

```bash
# Mutation: publish plausible-ce
# Response: {"data":{"templatePublish":null},"errors":[{"message":"Not Authorized","path":["templatePublish"]}]}
# Actual state after: PUBLISHED, code=plausible-ce, marketplace URL works
# Lesson: "Not Authorized" does not mean the mutation failed.
```

### Example 2: Re-publish Updates Don't Take Effect

```bash
# Mutation: update readme + image on already-published template
# Response: same "Not Authorized" wrapper
# Actual state after: image updated, readme NOT updated
# Lesson: Field-by-field persistence is inconsistent. Use dashboard for readme.
```

### Example 3: `templateUnpublish` Genuinely Failed

```bash
# Mutation: unpublish plausible-ce
# Response: "Not Authorized"
# Actual state after 3s sleep: status still PUBLISHED
# Lesson: Genuine failure. The user manually unpublished via dashboard.
```

### Example 4: `projectDelete` on Production Project Genuinely Failed

```bash
# Mutation: delete zucchini-generosity (production project)
# Response: "Not Authorized"
# Actual state after: project still present in workspace (22 projects)
# Lesson: Production projects may have additional protection. Use dashboard.
```

## Related Files

- `railway-graphql-template-introspection.md` — GraphQL mutation reference (also documents the misleading-error pattern)
- `template-publish-fields-and-restrictions.md` — Already-published templates are read-only via API
- `2026-06-29-railway-template-graphql-mutations.md` — Full mutation list (older reference)
- `SKILL.md` § "Pitfall: API Errors Are Misleading — Always Verify" (top-of-file summary)
