# Umami

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/umami)

Umami is a lightweight, open-source web analytics platform that provides insights into your website traffic without compromising privacy. It's self-hosted, GDPR-compliant, and offers real-time statistics with no cookie walls.

## Features

- **Real-time stats**: View live visitor counts, page views, and referrals instantly
- **Lightweight & fast**: Minimal footprint using PostgreSQL or MySQL as backend
- **Privacy-first**: No cookies required; fully GDPR compliant out-of-the-box
- **Self-hosted**: Full control over your analytics data and infrastructure
- **Easy deployment**: One-click deploy to Railway with automatic configuration
- **Dashboard & API**: Beautiful UI plus RESTful API for custom integrations

## Configuration

| Variable           | Description                                  | Default     | Required |
|--------------------|----------------------------------------------|-------------|----------|
| `DATABASE_URL`     | PostgreSQL database connection string        | (none)      | ✅ Yes   |
| `APP_URL`          | Public URL of your Umami instance            | (empty)     | ❌ No    |
| `WEBSITE`          | Default website name for new dashboards      | My Website  | ❌ No    |
| `SECRET_KEY`       | Secret key for session signing (auto-generated if empty) | (auto)      | ❌ No    |
| `TRUST_PROXY`      | Enable reverse proxy header trust            | false       | ❌ No    |

## License

This template is provided under the [MIT License](https://opensource.org/licenses/MIT). Umami itself is licensed under the same terms.