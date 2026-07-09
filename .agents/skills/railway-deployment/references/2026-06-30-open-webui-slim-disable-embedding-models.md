## open-webui v0.10.x Slim Image: Disable Embedding Model Downloads

**Problem**: The `ghcr.io/open-webui/open-webui:v0.10.1-slim` image still tries to download HuggingFace embedding models at startup despite Dockerfile ENV settings. This causes:
- 7-15 minute startup delays (waiting for HuggingFace)
- Memory bloat (>512MB baseline)
- Health check failures

**Root Cause Analysis**:
1. `config.py` line 962: `RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')` — hardcoded fallback
2. `retrieval/utils.py` line 1641: The `get_model_path()` function adds `'sentence-transformers/'` prefix to any model name without a `/`
3. Even with env vars set, the code path still attempts HuggingFace API calls

**Working Fix (tested 2026-06-30)**:

Two-layer approach required:

### Layer 1: Build-time Config Patch
```python
# docker-patch-config.py - replace hardcoded model names at build time
sentinel = "DISABLED_BY_HERMES/NO_MODEL/at_startup"  # Must have 2+ slashes

models_to_replace = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "all-MiniLM-L6-v2",
    "thenlper/gte-reranker-1.4",
    "thenlper/gte-reranker-base",
]

for model_name in models_to_replace:
    if model_name in modified_text:
        modified_text = modified_text.replace(model_name, sentinel)
```

The sentinel with 2+ slashes triggers early return in `get_model_path()`:
```python
if os.path.exists(model) or ('\\' in model or model.count('/') > 1) and local_files_only:
    return model  # Returns early WITHOUT network call
```

### Layer 2: Runtime Environment Variables
```dockerfile
ENV EMBEDDING_MODEL="" \
    OVERRIDE_EMBEDDING_MODEL="" \
    RAG_EMBEDDING_MODEL="" \
    OFFLINE_MODE=true \
    HF_HUB_OFFLINE=1 \
    ...other disable flags...
```

### Layer 3: Database Persistence
The SQLite database may cache old values. Either:
- Use a fresh volume for testing: `podman run -v fresh-volume:/data`
- Or run a one-time DB update on first container start

**Verification**:
```bash
# Build and test
podman build -t test-open-webui .
podman run -d --name test-open-webui -p 8081:8080 -v test-open-webui-data:/data test-open-webui
sleep 25
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/health

# Check logs for errors
podman logs test-open-webui | grep -E "huggingface|Sentence|model|Error"
# Should show NO HuggingFace download attempts
```

**Expected Result**: HTTP 200 response within ~30 seconds, memory <512MB, no HuggingFace downloads in logs.