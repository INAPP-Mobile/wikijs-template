# Umami Web Analytics

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/umami)

Umami is an open-source, lightweight web analytics platform that focuses on simplicity and privacy. It offers a Google Analytics alternative with built-in privacy features and minimal resource usage.

## Features

- 🍇 **Lightweight & Fast**: Minimal memory footprint (around 50MB per instance), super-fast queries
- 🔒 **Privacy-Focused**: No cookies, GDPR compliant by design
- 📊 **Real-Time Stats**: View page views and visitor stats in real-time
- 🎯 **Uptime Monitoring**: Track website uptime automatically
- 🔗 **Referral Source Tracking**: Identify where your traffic comes from
- 🌍 **Global Map**: See which countries visitors are from
- 📱 **Mobile and Desktop Stats**: Breakdown by device type
- ⚙️ **Customizable**: Filter by custom events, URLs, and referrers
- 💾 **PostgreSQL Database**: Performant and scalable data storage

## Configuration

| Config Variable | Description | Required | Default |
|-----------------|-------------|----------|---------|
| `DATABASE_URL`  | PostgreSQL connection string (from a managed database or provisioner) | Yes | - |
| `APP_SECRET_KEY` | Random secret key for session encryption | No | auto-generated |
| `TRACKING_SCRIPT_DOMAIN_LIMIT` | Maximum number of domains per tracking code | No | `10` |
| `MAX_EVENTS_PER_DAY` | Maximum events to store per day (in millions) | No | `5` |
| `API_TOKEN` | Token for API access and script integration | No | auto-generated |
| `APP_DOMAINS` | Allowed domain(s) for the app (add any required domain) | Yes | - |

## Quick Start

1. Click "Deploy on Railway" button above
2. Add a PostgreSQL database from the marketplace or create one
3. Connect the database to your Umami service
4. Set `APP_DOMAINS` to your deployment URL
5. Deploy and access your Umami dashboard
