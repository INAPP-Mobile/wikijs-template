# Session Reference: HTML-to-Markdown Converter Railway Template

Date: 2026-06-26
Repo: github.com/INAPP-Mobile/html-markdown-converter

## Work Done

- Added configurable Turndown options to POST /convert
- Added GET /health JSON endpoint
- Added CORS support
- Upgraded to multi-stage Dockerfile (Node 22, non-root user)
- Added railway.json, .dockerignore, .env.example
- Added integration tests via supertest
- Refactored app.ts from index.ts for testability
- Deployed to Railway, created and published template

## Key Railway CLI Commands Used

```bash
railway init -n "html-markdown-converter" --json
railway service source connect --repo INAPP-Mobile/html-markdown-converter --branch main --service html-markdown-converter --json
railway redeploy --from-source --yes
railway templates create --project dac95391-b01c-454d-995f-c1b24c9a6ffa --json
railway templates publish e199438d-0d7b-4503-b6b8-c94ba76d72cb --category "Other" --description "Converts HTML to Markdown via REST API. Deploy on Railway." --readme-file TEMPLATE.md --json
```

## Errors Encountered

1. "Unauthorized" on `service source connect` without `--branch main` — fixed by adding the flag
2. Template description >75 chars rejected — shortened to 75 chars
3. Template publish required specific README sections — created TEMPLATE.md with all 6 required sections

## Published Template

- Code: `html-markdown-converter`
- URL: https://railway.com/deploy/html-markdown-converter
