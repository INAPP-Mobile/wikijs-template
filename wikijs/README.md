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

## Dependencies for Running This Template

This template runs Wiki.js as a single Docker container. For PostgreSQL database support:

- A Railway account at https://railway.app
- PostgreSQL companion database (add via Railway UI or CLI)
- Environment variables set per template-vars.json

No additional infrastructure needed — all data persists in the mounted volume automatically.

Once deployed, access Wiki.js at your Railway-provided URL and create your first admin account on the setup wizard.

## Configuration

Copy .env.example to configure database credentials:

- DB_ENGINE: Database engine (postgres, mysql, sqlite) — default postgres
- DB_HOST: PostgreSQL/MySQL host — required when using postgres
- DB_PORT: Database port — default 5432
- DB_NAME: Database name — default wikijs
- DB_USER: Database user — default wikijs
- DB_PASS: Database password — auto-generated on first deploy
- PORT: Service port (Railway sets automatically) — default 3000
- APP_NAME: Display name of your wiki — default Wiki.js
- TIMEZONE: Server timezone — default UTC
- URL_BASE: Public URL (required after deploy for asset serving)
