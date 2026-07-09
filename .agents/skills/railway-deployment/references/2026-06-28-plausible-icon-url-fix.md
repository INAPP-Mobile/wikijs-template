# Plausible Template Icon URL Fix — 2026-06-28

## Problem

The published template `plausible-2` showed the generic Railway placeholder icon instead of the Plausible logo.

## Root Cause

The `pub-body.txt` pipeline body used the wrong URL format for the `--image` flag on `railway template publish`:

```bash
# WRONG - returns HTML page, not image
--image "https://github.com/INAPP-Mobile/railway-TEMPLATE_NAME/raw/main/template-icon.svg"

# CORRECT - returns raw SVG content
--image "https://raw.githubusercontent.com/INAPP-Mobile/railway-TEMPLATE_NAME/main/template-icon.svg"
```

The `github.com/.../raw/...` URL serves an HTML page (the GitHub file viewer), not the raw image content. Railway silently falls back to the default placeholder icon when the URL doesn't return an image.

## Fix Applied

Updated `pipeline-bodies/pub-body.txt` line 15 to use `raw.githubusercontent.com`.

## Lesson

**Always use `raw.githubusercontent.com` for `--image` URLs.** The `github.com` domain serves HTML pages with the file embedded in a viewer, while `raw.githubusercontent.com` serves the raw file content with correct MIME type. Railway's image validation likely checks the Content-Type header or response body.