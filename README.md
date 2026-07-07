# Umami

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/umami)

## Features

- **Privacy-focused**: No cookies, no trackers, fully GDPR compliant
- **Lightweight**: Minimal resource consumption and fast performance
- **Real-time analytics**: View visits in real-time without delays
- **Easy deployment**: One-click deploy to Railway with environment variables
- **Modern dashboard**: Clean, responsive UI for analyzing your data
- **Custom tracking**: Flexible tracking code integration

## Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `UMAMI_SECRET` | Encryption key for data security | auto-generated | Yes |
| `DATABASE_URL` | PostgreSQL database connection string | — | Yes |
| `WEBSITE_ID` | Identifier for your analytics website | auto-generated | No |

## License

MIT License. See [LICENSE](LICENSE) for details.
