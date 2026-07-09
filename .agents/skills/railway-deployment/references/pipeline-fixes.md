# Railway Pipeline Fixes & Learnings

## Worker Hangs on Large Prompts
**Symptom**: Pipeline hangs after "LLM running..." with `tcsetattr: Inappropriate ioctl device`
**Root Cause**: Worker tries to read stdin for large prompts
**Fix**: Add `stdin=subprocess.DEVNULL` to subprocess.run in `run_worker()` (core.py:107)
**Prevention**: Keep LLM prompts short (<500 chars); split big tasks into sequential small calls

## Volume Doesn't Attach After Deploy
**Symptom**: Volume defined in railway.json + railway.toml but not visible in deployed service
**Root Cause 1**: Missing `"name"` field in railway.json
**Root Cause 2**: Template was published BEFORE volume config was added — existing services don't get volumes retroactively
**Fix**: Add `"name": "Open WebUI"` to railway.json + delete/re-deploy service
**Validation**: Pipeline Step 8 now checks both files match

## Template Variables Show Empty in Deploy Form
**Symptom**: Deploy form shows generic "Value" labels, no defaults visible
**Expected**: Railway UI doesn't show `defaultValue` inline — it's applied behind scenes
**Clarification**: Normal behavior. Template-editor-raw.json `value` field IS the default.

## Pipeline Hangs on Step 0 Published Templates
**Symptom**: "Deterministic match: open-webui open-webui"
**Fix**: Use `--start-step N` to bypass dedup; create NEW template directory

## Step 1 LLM Timeout
**Fix**: Split validation into 4 small sequential calls instead of 1 monolithic prompt:
1. USER directive
2. EXPOSE 
3. HEALTHCHECK
4. Verify all

## Step 9 Draft Mode
**Behavior**: Pipeline now stops at draft stage only
**Manual publish**: `railway templates publish <code> --category <CAT> --readme-file README.md`
