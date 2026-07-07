# Umami v2.15.0 — bump when updating
FROM ghcr.io/umami-software/umami:postgresql-v2.15.0

LABEL org.opencontainers.image.source="https://github.com/INAPP-Mobile/railway-umami"

ENV PORT=3000
ENV DATABASE_URL="postgresql://postgres:postgres@localhost:5432/umami"

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-3000}/ || exit 1

USER node

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]