# Umami — bump when updating
FROM alpine:3.20

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-8080}/ || exit 1

# Create non-root user with UID/GID 1000 for security
RUN addgroup -g 1000 app && \
    adduser -u 1000 -G app -s /bin/sh -D app

USER app

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]