# 2026-07-02 — Template Audit Methodology

## When a User Reports a UI/Style Issue on a Deployed Template

### The Golden Rule: Test Upstream First

Before modifying the template, rule out whether the issue is **upstream application design** vs **template misconfiguration**.

**Method:**

1. **Pull and run the upstream image directly** (not the template's Dockerfile):
   ```bash
   docker run --rm -d -p <port>:<port> <upstream/image:tag>
   ```

2. **Curl the web root** to examine the raw HTML:
   ```bash
   curl -s http://localhost:<port>/ | head -50
   ```

3. **Check for CSS `<link>` tags or JS `<script>` tags** in the response. If there's no `<link rel="stylesheet">` in the upstream image itself, the template can't fix it — the app's HTML is embedded in the binary.

4. **Check that *template-provided* assets resolve:** if the HTML references external CSS/JS files, curl those paths too:
   ```bash
   curl -sI http://localhost:<port>/static/app.css | head -5
   ```

5. **Only then check the template** (Dockerfile, Nginx config, static file serving, etc.)

### Real Example: Blocky's "No CSS" Report

Blocky (DNS proxy, Go binary) serves a deliberately plain HTML page at `/`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>blocky</title>
</head>
<body>
    <h1>blocky</h1>
    <ul>
        <li><a href="/static/rapidoc.html">API Docs (RapiDoc)</a></li>
```
- **No CSS `<link>`** — this is how the upstream Go binary ships
- **Not a template flaw** — the template correctly ports the binary with no configuration loss
- **The /static/rapidoc.html page IS styled** (loads rapidoc-min.js) — users should navigate there for the rich UI
- **What IS a template flaw:** missing `healthcheckPath` in railway.json (Blocky returns 404 on `/health`), missing `builder: DOCKERFILE`

### Template Audit Checklist

Apply this to every template investigation:

| # | Check | Why |
|---|-------|-----|
| 1 | `railway.json` has `healthcheckPath` set to a 200-returning path | Default `/health` often 404 |
| 2 | `railway.json` has `builder: "DOCKERFILE"` explicit | Prevents auto-detection failures |
| 3 | README headings match Railway's exact format (`## Dependencies for`, not `## Dependencies for <App>`) | Publish/update will reject on mismatch |
| 4 | Upstream app CSS/JS assets resolve from the running container | Distinguishes template bug vs upstream design |
| 5 | `template-vars.json` exists or template variables are configured | Users see no config prompts if 0 vars |
| 6 | Deploy button URL uses the FINAL published code, not draft code | Draft code (from `templates create`) differs from final code (from `templates publish`) |
| 7 | `.env.example` doesn't contain hardcoded secrets or placeholder credentials | Security baseline |
| 8 | `Dockerfile` has HEALTHCHECK matching railway.json's `healthcheckPath` | Docker and Railway use separate health checks |
