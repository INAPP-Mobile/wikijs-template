# Railway Template Variables — Two-File Pattern

Railway template definitions use two JSON files with different schemas that must stay in sync. The pipeline auto-generates one from the other.

## File Roles

| File | Purpose | Schema |
|------|---------|--------|
| `template-vars.json` | Source of truth, pipeline reads this | `defaultValue`, `description`, `isOptional` |
| `template-editor-raw.json` | Deploy form JSON for Railway Dashboard template editor | `value`, `description` |

## Schema Reference

### template-vars.json (source of truth)

```json
{
  "VAR_NAME": {
    "defaultValue": "8080",
    "description": "What this controls",
    "isOptional": false
  }
}
```

- `defaultValue`: placeholder shown in the deploy form. **Never empty string** for required vars (breaks one-click install).
- `description`: meaningful explanation. Avoid "Configuration for X" boilerplate.
- `isOptional`: boolean. Secret vars use `"${{secret(32)}}"` as defaultValue — these are not optional even though they look like placeholders.

### template-editor-raw.json (deploy form)

```json
{
  "VAR_NAME": {
    "value": "8080",
    "description": "What this controls"
  }
}
```

- Only two fields: `value` (mapped from `defaultValue`) and `description`.
- The `_generate_template_editor_raw` function in `scripts/pipeline/core.py` (line ~1493) handles the conversion automatically.

## Pre-Publish Validation (step_8_pre_publish.py)

These checks run before publishing — fail any of them and the template is rejected:

| Check | Trigger |
|-------|---------|
| Empty default | `defaultValue` is `""` — breaks one-click install |
| Inline comments | `#` in defaultValue — Railway treats whole string as value |
| Placeholder secrets | required var (`isOptional: false`) using `"change-me"`, `"secret"`, or empty string instead of `${{secret(32)}}` |
| Bad isOptional type | not a boolean |
| Weak description | matches `/^Configuration set|^Configure/i` or `< 10` chars |

## Which File to Edit

Always edit `template-vars.json` first. Run `_generate_template_editor_raw(template_dir)` to regenerate the deploy form. Edit `template-editor-raw.json` only if you need deploy-form-only overrides (rare).

Minimal fallback when no env vars exist:

```json
{"PORT": {"defaultValue": "8080", "description": "Port service listens inside container", "isOptional": true}}
```

## Pitfall: Secret Placeholders

Required vars that need secrets **must** use the exact pattern:

```
"${{secret(32)}}"
```

Do NOT use `"changeme"`, `"secret"`, `""`, or any other placeholder. The pre-publish check flags all of these as failures.
