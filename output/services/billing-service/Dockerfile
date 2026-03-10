# FastAPI service Dockerfile for billing-service
# Build context: Repository root (../..)
# Usage: docker build -f services/billing-service/Dockerfile --target development -t billing-service:dev ../../

# Use Python 3.11 slim as base
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Copy and install venturestrat-models SDK (namespace package)

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

# Copy registry-service SDK (for venturestrat-registry)
# Copy schema-registry package (for venturestrat-schema-registry)
# Copy service files (including README.md for pyproject.toml)
COPY services/billing-service /app/services/billing-service

# Install development dependencies
WORKDIR /app/services/billing-service
RUN pip install --no-cache-dir -e .[dev]

# Install in development mode
RUN pip install -e .

# Expose ports
EXPOSE 8063

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8063/health/live || exit 1

# Development command
CMD ["python", "-m", "billing_service"]

# Production stage
FROM base as production

# Copy and install venturestrat-models SDK (namespace package)
COPY sdk/venturestrat-models /app/sdk/venturestrat-models
RUN pip install --no-cache-dir -e /app/sdk/venturestrat-models

# Copy registry-service SDK (for venturestrat-registry)
COPY services/registry-service/sdk /app/services/registry-service/sdk

# Copy schema-registry package (for venturestrat-schema-registry)
COPY packages/schema-registry /app/packages/schema-registry

# Copy service files
COPY services/billing-service /app/services/billing-service

# Install production dependencies
WORKDIR /app/services/billing-service
RUN pip install --no-cache-dir .

# Create non-root user
RUN groupadd -r billing_service && useradd -r -g billing_service billing_service
RUN chown -R billing_service:billing_service /app
USER billing_service

# Expose ports
EXPOSE 8063

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8063/health/live || exit 1

# Production command
CMD ["python", "-m", "billing_service"]
