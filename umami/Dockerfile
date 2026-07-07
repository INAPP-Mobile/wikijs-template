# Umami — bump when updating
FROM alpine:3.20

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-8080}/ || exit 1

USER node

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]