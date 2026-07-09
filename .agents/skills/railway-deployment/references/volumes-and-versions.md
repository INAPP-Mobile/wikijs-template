## Volume Bindings — Must Match Exactly Both Files

A volume must exist in **both** `railway.json` AND `railway.toml` with the **same name**:
```json
// railway.json
"volumeMounts": [{"name": "open-webui-data", "mountPath": "/data"}]
```
```toml
# railway.toml
[[deploy.volumeMounts]]
name = "open-webui-data"
mountPath = "/data"
```

**Symptom of mismatch**: Deploy form shows `2 variable values needed` (PORT + WEBUI_SECRET_KEY) but no volume appears under Settings > Volumes after deployment.

**Verification**: `_validate_volume_mounts()` (from `scripts/pipeline/step_8_pre_publish.py`) flags mismatches in Step 7 and Step 8.

## Hardcoded Versions are Correct (NOT :latest)

**AGENTS.md Rule for Railway templates**: Always pin to exact version. Never use `:latest`.
- Update manually: `v0.10.1-slim` → `v0.10.2-slim` when ready
- Comment above: `# open-webui version: bump when updating`
- Pipeline Step 1 checks `:latest` and blocks it
- Pipeline Step 1 also queries GitHub API and warns if pinned version is behind upstream

**Verify version**:
```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/releases/latest" | grep tag_name
```

## Pipeline LLM Worker Timeout

`call_worker(prompt, step_name="Step N")` requires `step_name` argument (mandatory positional).

If `worker` backend (Hermes agent) hangs or is slow:
- Pipeline subprocess may get killed (SIGTERM) by terminal
- Use `background=true` with `notify_on_complete=true` and poll
- Pipeline steps cannot be rushed — LLM inference takes time
- Don't kill pipeline prematurely — wait for worker to finish

## Step 0 Behavior on Already-Published Templates

Step 0 performs deterministic dedup. If a base image already matches a published template (e.g., `open-webui` matches `railway-open-webui`), Step 0 returns NO-GO.

**This is expected.** Pipeline requires `--start-step N` to skip Step 0 when working with existing published templates.

## Pipeline Stops at Draft Stage (Not Production)

Step 9 (since v2.1 update) generates `template-vars.json` and `template-editor-raw.json`, creates/updates a **draft** template, and outputs the draft URL:

```
DRAFT TEMPLATE READY FOR REVIEW:
  Code: open-webui-3
  URL:  https://railway.com/dashboard/templates/open-webui-3/editor
```

Manual publish required:
```bash
railway templates publish <code> --category <CAT> --description "..." --readme-file README.md
```
