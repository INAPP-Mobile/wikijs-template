# Volume Validation in Railway Templates

## Problem
Railway does not auto-create volumes from Dockerfile `VOLUME` directives. They must be declared in `railway.json` AND `railway.toml` or data is lost on restart.

## Validation Checklist

1. Every `VOLUME` in Dockerfile → must exist in `railway.json` `deploy.volumeMounts[]`
2. Every entry in `railway.json` volumeMounts → must exist in `railway.toml` under `[[deploy.volumeMounts]]`
3. `railway.json` **MUST** include `"name"` field (without it, volumes silently fail to attach)

## Pipeline Script

`scripts/pipeline/step_8_pre_publish.py` includes `_validate_volume_mounts()`:

```python
def _validate_volume_mounts(template_dir: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    json_path = template_path(template_dir, "railway.json")
    toml_path = template_path(template_dir, "railway.toml")

    # Parse railway.json volumes
    json_volumes: list[dict] = []
    if json_path.is_file():
        try:
            parsed = json.loads(json_path.read_text())
            json_volumes = parsed.get("deploy", {}).get("volumeMounts", [])
        except Exception:
            pass

    # Parse railway.toml volumes
    toml_text = toml_path.read_text() if toml_path.is_file() else ""
    toml_volume_names: set[str] = set()
    for line in toml_text.splitlines():
        line = line.strip()
        if line.startswith("name"):
            m = re.match(r'name\s*=?\s*"?([^"\s\]]+)"?', line)
            if m:
                toml_volume_names.add(m.group(1))

    # Check 1: json volumes must exist in toml
    for vol in json_volumes:
        vol_name = vol.get("name", "")
        if vol_name and vol_name not in toml_volume_names:
            issues.append(f"Volume '{vol_name}' in railway.json but not in railway.toml")

    # Check 2: warn if no volumes but Dockerfile references /data or /var paths
    if not json_volumes:
        dockerfile_path = template_path(template_dir, "Dockerfile")
        if dockerfile_path.is_file():
            df_text = dockerfile_path.read_text()
            for pattern in (r'/data\b', r'/var/www', r'/var/lib', r'/home/\w+\.'):
                if re.search(pattern, df_text):
                    issues.append("No volumeMounts but Dockerfile references persistent paths")
                    break

    return (len(issues) == 0, issues)
```

## Debugging Missing Volumes

If volumes don't appear in deployed service:

1. Check `railway.json` has `"name"` field
2. Check `railway.toml` mirrors `railway.json` volumeMounts exactly
3. Re-run pipeline Step 8: `python scripts/pipeline.py railway-<name> --start-step 8`
4. Re-publish template: `railway templates update <code> --...`
5. Delete old service and re-deploy (volumes NOT retroactive)
