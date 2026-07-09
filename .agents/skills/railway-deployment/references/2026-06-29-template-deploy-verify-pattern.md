# 2026-06-29 — Template E2E Deploy Verification Pattern

## Session Summary
User asked to break the monolithic deploy task into smaller phases, resulting in D3: E2E Deploy Verification. This task simulates how an end-user would deploy the published template.

## Pattern: Deploy Published Template as End-User

After a template is published (D2), the E2E deploy verification creates a fresh Railway project and deploys the template exactly as a user would from the marketplace.

### Key Steps

```bash
# 1. Create a fresh test project
railway init --name <template-name>-e2e

# 2. Deploy the published template
railway deploy --template <TEMPLATE_CODE>

# 3. Set required runtime variables (if template has required vars)
railway variable set KEY=value -s <service-name> --skip-deploys

# 4. Trigger deployment
railway up --detach

# 5. Wait for deployment to complete
railway deployment list --json

# 6. Verify health endpoint
curl -f https://<deployment-url>/<health-path>

# 7. Capture screenshots for report
#    - Dashboard showing running service
#    - App homepage / health endpoint
#    - Deployment status page
```

### Why Not Reuse the Source Project?

The source project (used in D1 to create the draft) is a development project — it has GitHub source linkage, deploy history, etc. Creating a fresh project simulates a clean end-user deployment and catches issues like:
- Missing template variables (required vars not set)
- Wrong source reference in template
- Template code doesn't resolve to correct manifest
- Network issues with template-based provisioning

### Variables to Set on Deploy Project

| Variable | Source | Example |
|----------|--------|---------|
| `DATABASE_URL` | Auto-provisioned or user-provided | `postgresql://...` |
| `SECRET_KEY` | Use `openssl rand -hex 32` | Random 64-char hex |
| App-specific config | From template description | `DEBUG=false` |

### Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Template not found` | TEMPLATE_CODE wrong / template unpublished | Re-publish, recheck code |
| `Missing required variable` | Template has required var without default | Add variable to deploy project |
| Health check fails | Wrong healthcheck path in railway.json | Fix `healthcheckPath` in source |
| Build fails | Dockerfile issue or missing files | Fix in source repo, re-create draft |

## Report Template

```markdown
# Deployment Verification: <template-name>

**Status**: SUCCESS/FAILED
**Template Code**: <code>
**Deployment URL**: https://<url>
**Timestamp**: <ISO 8601>

## Variables Set
- KEY1=*** (redacted)
- KEY2=***

## Health Check
- Path: /health
- Status: 200 OK
- Response Time: 230ms

## Screenshots
- assets/deploy-dashboard.png
- assets/deploy-app.png
- assets/deploy-status.png

## Issues
- None / Description of fix applied
```

## Related

- `references/2026-06-29-service-vs-template-variables.md` — Distinction between service and template vars
- `references/2026-06-29-template-variable-config-dashboard.md` — Manual variable config step
- `references/2026-06-29-railway-template-kanban-pipeline.md` — Full pipeline overview
