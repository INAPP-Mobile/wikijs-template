# Deploy and Host Wiki.js on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/wikijs)

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
3. Add a PostgreSQL service from the Integrations tab (Search "Postgres" in Marketplace, click Connect)
4. Once deployed, access Wiki.js at `https://your-app-name.up.railway.app`
5. Complete the setup wizard to create your admin account and configure settings

### First-Time Setup

After deployment:

1. Browse to your Railway-provided URL (e.g., `https://wikijs-template-production.up.railway.app`)
2. Create your first admin account via the setup wizard
3. Configure your wiki — set site name, logo, language, and theme in Settings > General
4. (Optional) Set up authentication — Wiki.js supports OAuth2, LDAP, SAML 2.0, OpenID Connect

### Postgres Setup

If using PostgreSQL:

1. Add a Redis cache service for session storage (search "Redis" in Marketplace, click Connect)
2. Set the `REDIS_HOST` variable to your Redis service host from the Variables tab
3. Wiki.js will use the default database credentials (DB_USER, DB_PASS) on the wikijs-app service

## Configuration

Copy .env.example to configure database credentials:

- DB_ENGINE: Database engine (postgres, mysql, sqlite) - default postgres
- DB_HOST: PostgreSQL/MySQL host - required when using postgres
- DB_PORT: Database port - default 5432
- DB_NAME: Database name - default wikijs
- DB_USER: Database user - default wikijs
- DB_PASS: Database password - auto-generated on first deploy
- PORT: Service port (Railway sets automatically) - default 3000
- APP_NAME: Display name of your wiki - default Wiki.js
- TIMEZONE: Server timezone - default UTC
- URL_BASE: Public URL (required after deploy for asset serving)

## Troubleshooting

**"Connection refused" on database:** Ensure you've connected a postgres service from the Integrations tab and the DB_HOST points to it.

**Pages returning 404 or blank:** Set your `URL_BASE` in the Variables tab to match your deployed URL (including protocol).

**White screen after setup:** Clear browser cache or try incognito mode; verify the database schema was updated on first boot by checking the build logs for "Database Connection Successful".

## License

This template is released under the [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) license.
Wiki.js itself (the application being deployed) is developed by requarks and licensed under AGPL-3.0 as well.
