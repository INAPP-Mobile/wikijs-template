# Umami - Simple Web Analytics Template for Railway

> A lightweight, privacy-friendly analytics dashboard that you can deploy to Railway in minutes.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/umami)

## Features

- 🚀 **One-click deployment** - Get up and running with zero configuration
- 📊 **Real-time analytics** - Track page views, visitors, and more
- 🔒 **Privacy-first** - No cookies or tracking scripts that violate user privacy
- 🎨 **Clean dashboard** - Beautiful, intuitive interface for analyzing your data
- ⚡ **Auto-updates** - Stay current with the latest Umami releases automatically
- 💾 **Managed database** - PostgreSQL included via Railway's database add-on

## Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_TYPE` | Database type (postgresql) | `postgresql` | No |
| `PGHOST` | PostgreSQL host (auto-filled by Railway) | - | Yes (if not using managed db) |
| `PGUSER` | PostgreSQL username | - | Yes (if not using managed db) |
| `PGPASSWORD` | PostgreSQL password | - | Yes (if not using managed db) |
| `PGDATABASE` | Database name | `umami` | No |
| `APP_SECRET` | Application secret key for security | Auto-generated | No |
| `TELEMETRY_ENABLED` | Enable anonymous usage tracking | `true` | No |

## License

This template is MIT licensed. See [LICENSE](LICENSE) for details.