# VentureStrat Registry Service
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Copy monorepo packages (workaround for devpi-client bug)
# NOTE: Build context must be monorepo root for these paths to work
COPY packages/observability /app/packages/observability
COPY packages/venturestrat-service-base /app/packages/venturestrat-service-base

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

# Install monorepo packages as editable (enables hot reload)
RUN pip install -e /app/packages/venturestrat-service-base \
    && pip install -e /app/sdk/venturestrat-models \
    && pip install -e /app/sdk/venturestrat-tenancy
# Install dev dependencies
COPY services/registry-service/pyproject.toml services/registry-service/README.md ./
RUN pip install -e ".[dev]"

# Copy migration configuration
COPY services/registry-service/alembic.ini ./
COPY services/registry-service/migrations/ migrations/

# Copy source code
COPY services/registry-service/src/ src/
COPY services/registry-service/tests/ tests/

# Expose ports (REST and gRPC)
EXPOSE 8080 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health/live || exit 1

# Set Python path to include src
ENV PYTHONPATH=/app/src

# Run with hot reload for development
CMD ["uvicorn", "registry.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# Production stage
FROM base as production

# Copy monorepo packages (workaround for devpi-client bug)
# NOTE: Build context must be monorepo root for these paths to work
COPY packages/observability /app/packages/observability
COPY packages/venturestrat-service-base /app/packages/venturestrat-service-base
COPY sdk/venturestrat-models /app/sdk/venturestrat-models
COPY sdk/venturestrat-tenancy /app/sdk/venturestrat-tenancy

# Install monorepo packages
RUN pip install /app/packages/observability && \
    pip install /app/packages/venturestrat-service-base && \
    pip install /app/sdk/venturestrat-models && \
    pip install /app/sdk/venturestrat-tenancy

# Copy only production dependencies
COPY services/registry-service/pyproject.toml services/registry-service/README.md ./
RUN pip install .

# Copy migration configuration
COPY services/registry-service/alembic.ini ./
COPY services/registry-service/migrations/ migrations/

# Copy source code
COPY services/registry-service/src/ src/

# Create non-root user
RUN useradd -m -u 1000 registry && chown -R registry:registry /app
USER registry

# Expose ports
EXPOSE 8080 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health/live || exit 1

# Set Python path to include src
ENV PYTHONPATH=/app/src

# Run production server
CMD ["uvicorn", "registry.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
