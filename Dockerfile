# =============================================================================
# Dockerfile: Wiki.js 2.x on Railway – PostgreSQL primary, SQLite fallback
# Docker image source: https://hub.docker.com/r/requarks/wiki
# Project:          https://github.com/requarks/wiki
# License:          AGPL-3.0
# =============================================================================

FROM requarks/wiki:2.5.314

ARG BUILD_YEAR=2026

LABEL org.opencontainers.image.title="Wiki.js" \
      org.opencontainers.image.description="A modern, lightweight wiki and knowledge base with markdown support." \
      org.opencontainers.image.source="https://github.com/requarks/wiki" \
      org.opencontainers.image.vendor="Requarks" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.created="${BUILD_YEAR}-07-02T00:00:00Z"

ENV WIKI_PORT=3000 \
    NODE_ENV=production \
    TZ=UTC \
    DB_TYPE=sqlite \
    DB_FILEPATH=/wiki/data/wikijs.db

RUN mkdir -p /wiki/data && chown node:node /wiki/data

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ping || exit 1

EXPOSE 3000

VOLUME ["/wiki/data"]
