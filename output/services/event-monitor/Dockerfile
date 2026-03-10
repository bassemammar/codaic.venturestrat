# Event Monitor service — lightweight observer
# Build context: Repository root (../..)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy only manifest files for topology parsing (lightweight)

# Copy and install SDK packages
COPY sdk/venturestrat-models /app/sdk/venturestrat-models
COPY sdk/venturestrat-tenancy /app/sdk/venturestrat-tenancy
COPY sdk/venturestrat-security /app/sdk/venturestrat-security
COPY sdk/venturestrat-audit /app/sdk/venturestrat-audit
RUN pip install --no-cache-dir -e /app/sdk/venturestrat-models \
    && pip install --no-cache-dir -e /app/sdk/venturestrat-tenancy \
    && pip install --no-cache-dir -e /app/sdk/venturestrat-security \
    && pip install --no-cache-dir -e /app/sdk/venturestrat-audit

# Copy shared packages
COPY packages/venturestrat-service-base /app/packages/venturestrat-service-base
COPY packages/observability /app/packages/observability
COPY packages/venturestrat-manifest /app/packages/venturestrat-manifest
COPY packages/schema-registry /app/packages/schema-registry
COPY packages/codaic-events /app/packages/codaic-events
RUN pip install --no-cache-dir -e /app/packages/venturestrat-service-base \
    && pip install --no-cache-dir -e /app/packages/observability \
    && pip install --no-cache-dir -e /app/packages/venturestrat-manifest \
    && pip install --no-cache-dir -e /app/packages/schema-registry \
    && pip install --no-cache-dir -e /app/packages/codaic-events

COPY services/investor-service/manifest.yaml /app/services/investor-service/manifest.yaml
COPY services/outreach-service/manifest.yaml /app/services/outreach-service/manifest.yaml
COPY services/crm-service/manifest.yaml /app/services/crm-service/manifest.yaml
COPY services/billing-service/manifest.yaml /app/services/billing-service/manifest.yaml
COPY services/event-monitor/manifest.yaml /app/services/event-monitor/manifest.yaml

# Copy event-monitor service
COPY services/event-monitor /app/services/event-monitor

# Install
WORKDIR /app/services/event-monitor
RUN pip install --no-cache-dir .

EXPOSE 8101

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8101/health/live || exit 1

ENV SERVICES_DIR=/app/services

CMD ["python", "-m", "event_monitor"]
