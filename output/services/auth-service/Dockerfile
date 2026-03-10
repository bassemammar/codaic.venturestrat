# FastAPI service Dockerfile for auth-service
# Build context: Repository root (../..)
# Usage: docker build -f services/auth-service/Dockerfile --target development -t auth-service:dev ../../

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

# Copy and install venturestrat-tenancy SDK
# Copy and install venturestrat-security SDK
# Copy and install venturestrat-audit SDK
# Copy registry-service SDK (for venturestrat-registry)
# Copy schema-registry package (for venturestrat-schema-registry)
# Copy service files (including README.md for pyproject.toml)
COPY services/auth-service /app/services/auth-service

# Install development dependencies
WORKDIR /app/services/auth-service
RUN pip install --no-cache-dir -e .[dev]

# Install in development mode
RUN pip install -e .

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Development command
CMD ["python", "-m", "auth_service"]

# Production stage
FROM base as production

# Copy and install venturestrat-models SDK (namespace package)
COPY sdk/venturestrat-models /app/sdk/venturestrat-models
RUN pip install --no-cache-dir -e /app/sdk/venturestrat-models

# Copy and install venturestrat-tenancy SDK
COPY sdk/venturestrat-tenancy /app/sdk/venturestrat-tenancy
RUN pip install --no-cache-dir -e /app/sdk/venturestrat-tenancy

# Copy and install venturestrat-security SDK
COPY sdk/venturestrat-security /app/sdk/venturestrat-security
RUN pip install --no-cache-dir -e /app/sdk/venturestrat-security

# Copy and install venturestrat-audit SDK
COPY sdk/venturestrat-audit /app/sdk/venturestrat-audit
RUN pip install --no-cache-dir -e /app/sdk/venturestrat-audit

# Copy registry-service SDK (for venturestrat-registry)
COPY services/registry-service/sdk /app/services/registry-service/sdk

# Copy schema-registry package (for venturestrat-schema-registry)
COPY packages/schema-registry /app/packages/schema-registry

# Copy service files
COPY services/auth-service /app/services/auth-service

# Install production dependencies
WORKDIR /app/services/auth-service
RUN pip install --no-cache-dir .

# Create non-root user
RUN groupadd -r auth_service && useradd -r -g auth_service auth_service
RUN chown -R auth_service:auth_service /app
USER auth_service

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Production command
CMD ["python", "-m", "auth_service"]
