# Deploy and Host Wiki.js on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/wikijs-template)

Wiki.js is a modern, lightweight, and highly powerful wiki and knowledge base platform with robust markdown support. One-click deploy on Railway with optional PostgreSQL companion database.

## About Hosting

Wiki.js (requarks/wiki) provides a full-featured wiki experience with:

- Beautiful, responsive UI with real-time editing
- Markdown, WYSIWYG, and drag-and-drop editors
- Role-based access control
- Multi-language support
- REST API for integrations
- Support for PostgreSQL, MySQL, MariaDB, SQL Server, and SQLite
- Docker-based deployment on any platform

Deploying on Railway means you get automatic HTTPS, zero-config storage, and continuous updates.

## Why Deploy Wiki.js

Wiki.js is one of the most popular open-source wiki solutions because it offers:

- Zero cost — completely free and open source (AGPL-3.0)
- Modern editor — Markdown, WYSIWYG, or code editor modes
- Powerful search — full-text search across all pages
- Version control — track changes, roll back, diff history
- Themes and templates — customize the look and feel
- OAuth2/LDAP/SSO — integrate with your identity provider

## Common Use Cases

1. Team Documentation — centralize wikis for engineering, product, marketing teams
2. Project Knowledge Base — track decisions, architecture, API docs, runbooks
3. Personal Notes and Planning — structured knowledge management for individuals
4. Open Source Project Docs — public-facing documentation portals with versioning

## Deploy

Click the button above to deploy Wiki.js on Railway. You will be prompted to:

1. Create a new project in your Railway workspace or select an existing one
2. Wait for the automatic build and deployment (usually 1-3 minutes)
3. Add a PostgreSQL companion database service from the Integrations tab
4. Once deployed, access Wiki.js at your Railway-provided URL (e.g., `https://wikijs-template-production.up.railway.app`)
5. Complete the setup wizard to create your admin account and configure settings

### First-Time Setup

After deployment:

1. Browse to your Railway-provided URL
2. Create your first admin account via the setup wizard
3. Configure your wiki — set site name, logo, language, and theme in Settings > General
4. (Optional) Set up authentication — Wiki.js supports OAuth2, LDAP, SAML 2.0, OpenID Connect

### Postgres Setup

If using PostgreSQL:

1. Add a Redis cache service for session storage from the Integrations tab
2. Set the `REDIS_HOST` variable to your Redis service host from the Variables tab
3. Wiki.js will use the database credentials (DB_USER, DB_PASS) configured on wikijs-app

## Configuration

Copy `.env.example` to configure database credentials:

- **DB_TYPE**: Database engine type — default `postgres`
- **DB_HOST**: PostgreSQL/MySQL host — required when using postgres
- **DB_PORT**: Database port — default 5432
- **DB_NAME**: Database name — default `wikijs`
- **DB_USER**: Database user — default `wikijs`
- **DB_PASS**: Database password — auto-generated on first deploy, must be set for non-postgres
- **PORT**: Service port (Railway sets automatically) — default 3000
- **WIKI_PORT**: Wiki.js application port — default 3000
- **URL_BASE**: Public URL (required after deploy for asset serving)

## Environment Variables

The template includes the following configurable variables. Edit them in your Railway project's Variables tab to customize behavior.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| DB_TYPE  | Required | `postgres` | Database engine type (postgres, mysql, sqlite) |
| DB_HOST  | Optional | `db-postgres` | PostgreSQL or MySQL host address |
| DB_PORT  | Optional | `5432` | Database port number |
| DB_NAME  | Optional | `wikijs` | Name of the database to connect to |
| DB_USER  | Optional | `wikijs` | Username for database authentication |
| DB_PASS  | Required | *(auto-set)* | Secret: password for database connections, use `${{ generate(32) }}` template function in production |
| WIKI_PORT | Required | `3000` | Application listen port (must match PORT variable) |

> **Important**: Set `URL_BASE` to your application's public URL after deployment so all static assets and links resolve correctly.

### Template Functions for Secrets

When setting DB_PASS in production, use Railway's secret generator:

```
DB_PASS = ${{ generate(32) }}
```

This generates a cryptographically secure random 32-character string that remains hidden in UI logs and the API.

## Troubleshooting

**"Connection refused" on database**: Ensure you've connected a postgres service from the Integrations tab and the DB_HOST points to it. Verify the connection via `railway exec -s wikijs-app 'psql $DATABASE_URL'`.

**Pages returning 404 or blank**: Set your `URL_BASE` variable in the Railway Variables tab to match your deployed URL (including protocol), e.g., `https://your-app.up.railway.app`.

**White screen after setup**: Clear browser cache or try incognito mode; verify the database schema was updated on first boot by checking build logs for "Database Connection Successful".

## Dependencies for wikijs-template

This template depends on the following services being configured in your Railway project:

- **wikijs-app**: The main Wiki.js application container (auto-configured from this repository)
- **PostgreSQL database**: Optional but recommended; add via `railway add postgres --service wikijs-app` and connect from the Integrations tab
- **Redis** (optional): For session storage in multi-process deployments; add via `railway add redis --service wikijs-app`

### Deployment Dependencies

| Service | Purpose | Required? | How to Add |
|---------|---------|-----------|------------|
| postgresql | Persistent metadata and content storage | Recommended for production | Railway Marketplace > Postgres > Connect |
| Redis | Session cache (multi-process mode) | Optional, recommended | Railway Marketplace > Redis > Connect |

## License

This template is released under the MIT license. Wiki.js itself (the application being deployed) uses the [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) license.
