# =============================================================================
# Dockerfile: Wiki.js 2.x on Railway (PostgreSQL)
# Docker image source: https://hub.docker.com/r/requarks/wiki
# Project:          https://github.com/requarks/wiki
# License:          AGPL-3.0
# =============================================================================
# NOTE: Do NOT add a `VOLUME` instruction — Railway rejects it; use Railway
# Volumes (volumeMounts in railway.json) instead.
# NOTE: Do NOT add a custom `HEALTHCHECK` — Railway runs its own /ping check.
# NOTE: Do NOT hardcode the listen port; Wiki.js reads the injected PORT env.

FROM requarks/wiki:2.5.314

ARG BUILD_YEAR=2026

LABEL org.opencontainers.image.title="Wiki.js" \
      org.opencontainers.image.description="A modern, lightweight wiki and knowledge base with markdown support." \
      org.opencontainers.image.source="https://github.com/requarks/wiki" \
      org.opencontainers.image.vendor="Requarks" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.created="${BUILD_YEAR}-07-02T00:00:00Z"

ENV NODE_ENV=production \
    TZ=UTC \
    DB_TYPE=postgres \
    DB_HOST=postgres.railway.internal \
    DB_PORT=5432 \
    DB_NAME=wikijs \
    DB_USER=postgres \
    DB_PASS=postgres

RUN mkdir -p /wiki/data && chown node:node /wiki/data

EXPOSE 3000
