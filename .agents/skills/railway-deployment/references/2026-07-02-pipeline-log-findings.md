# Pipeline Log Analysis (2026-07-02)

Findings from reviewing `pipeline-logs/deploy-publish-v3.log` and related logs.

## Bug 1: `railway project delete` positional arg silently fails

Every log run shows this repeated error:
```
--- attempting delete beb403ea-b006-4f5a-84e9-23205657c3e8 ---
error: unexpected argument 'beb403ea-b006-4f5a-84e9-23205657c3e8' found
Usage: railway project delete [OPTIONS]
```

The CLI does NOT accept a project ID as a positional argument. Correct:
```bash
railway project delete --project <UUID> --yes   # ✅ works
railway project delete <UUID> --yes              # ❌ "unexpected argument"
```

This is doubly dangerous because it exits with code 0 on failure, so scripts think it succeeded.

**Fix applied to:** `railway-template-publish-pipeline` helper scripts (`railway-cli.py`, `teardown.py`), `railway-deployment` skill (commands table + teardown section + pitfall).

## Bug 2: `railway domain status` never transitions from CREATING

In both `deploy-publish-v3.log` and `deploy-publish-attempt.log`, 6-8 health probes all show:
```
Sync status: CREATING
HTTP=000
```

The `railway domain status` command always returns CREATING during the polling window. The domain eventually becomes ACTIVE but takes much longer than the probe loop waits. The correct approach is to curl the deploy URL directly (`https://<slug>.up.railway.app`) instead of polling `railway domain status`.

**Fix applied to:** `railway-template-publish-pipeline` helper scripts (`deploy-and-verify.py` curls the URL directly).

## Bug 3: `templates create` does NOT accept `--workspace`/`--category`/`--description`

The shell script and early helper script both passed these flags to `templates create`, but it only accepts `--project`, `--environment`, `--json`. Workspace, category, and description go on `templates publish`.

**Fix applied to:** `railway-template-publish-pipeline` helper scripts (`publish-template.py`).

## Bug 4: Template not found on publish

Both logs show `Template "homepage" not found` because `templates create` was never called before `templates publish`. The pipeline skipped the create step. Root cause: the shell pipeline was missing the `templates create` step entirely — it went directly from deploy to publish.

**Fix:** The `publish-template.py` script now explicitly chains create → publish and extracts the template ID from `templates create --json` output.
