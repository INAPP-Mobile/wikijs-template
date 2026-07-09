# First-Step Diagnostics: railway.toml Syntax Validation

When a Railway deployment fails immediately with **"Deployment does not have an associated build"**, the FIRST thing to check is `railway.toml` syntax. A single malformed line silently prevents ALL builds from starting — no build logs, no error output, just this message.

## The Pitfall: `key "value"` vs `key = "value"`

TOML requires the `=` sign. This is wrong:

```toml
[project]
name "plausible"     ← WRONG: missing =

[[services]]
id "plausible"       ← WRONG: missing =
name "Plausible CE"  ← WRONG: missing =
```

This is correct:

```toml
[project]
name = "plausible"

[[services]]
id = "plausible"
name = "Plausible CE"
```

Hand-editing `.toml` files (or copy-pasting from docs) frequently drops the `=`. Railway's parser then rejects the entire file, and the only symptom is "Deployment does not have an associated build" from `railway up`.

## Diagnostic Flow

When build fails with "no associated build":

```bash
# 1. Validate TOML syntax
python3 -c "import tomllib; tomllib.load(open('railway.toml','rb')); print('OK')"
# If invalid: tomllib.TOMLDecodeError with line number

# 2. Check for common mistakes
grep -nE '^\w+ "[^"]*"$' railway.toml  # finds key "value" patterns (no =)
grep -nE '^\w+ [^"=]' railway.toml      # finds other non-assignment lines

# 3. Fix by adding = signs, then re-deploy
```

## Why This Happens

- Railway's `railway up` reads `railway.toml` to determine service structure
- If TOML is invalid, service definitions are silently dropped
- Result: empty service list, no build queued, no error message about TOML
- The SAME error (`"Deployment does not have an associated build"`) also appears for projects with no services — so always rule out TOML syntax first

## Prevention

When writing `railway.toml` via `write_file` or `patch`, the TOML linter may flag issues. But the linter only warns — it won't stop a syntactically-invalid file from being written. Always validate after writing:

```bash
python3 -c "import tomllib; tomllib.load(open('railway.toml','rb'))"
```

## Lesson From Session

User asked "Why can't you deploy from this repo?" pointing at `github.com/INAPP-Mobile/railway-plausible`. Investigation went sideways (creating new projects, copying configs) for multiple turns before discovering the root cause: the repo's own `railway.toml` had `key "value"` instead of `key = "value"` — a one-character typo that paralyzed ALL deployments.

**Rule:** When user provides a specific source ref (URL, repo name, file path), investigate THAT directly before starting tangential debugging. The answer is usually in the source they pointed at.
