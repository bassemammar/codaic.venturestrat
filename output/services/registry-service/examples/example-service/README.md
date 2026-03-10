# Example Service

This example demonstrates how to use the VentureStrat Registry SDK for service registration and discovery.

## Overview

The example service shows:
- Auto-registration using `manifest.yaml`
- Automatic deregistration on shutdown
- Discovering dependencies (market-data-service)
- Health check endpoints

## Files

- `manifest.yaml` - Service descriptor defining name, version, dependencies, and health checks
- `main.py` - FastAPI service with SDK integration

## Running the Example

### Prerequisites

1. Start the registry service:
   ```bash
   cd services/registry-service
   docker-compose -f docker-compose.dev.yaml up -d
   ```

2. Install the SDK:
   ```bash
   cd services/registry-service/sdk
   pip install -e .
   ```

### Start the Example Service

```bash
cd examples/example-service
python main.py
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_HOST` | `127.0.0.1` | Host address to bind |
| `SERVICE_PORT` | `8000` | Port to listen on |
| `REGISTRY_HOST` | `localhost` | Registry service host |
| `REGISTRY_PORT` | `8080` | Registry service port |

### Health Endpoints

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe (checks dependencies)

### API Endpoints

- `GET /api/v1/example/dependencies` - List discovered dependencies

## How It Works

1. On startup, the service reads `manifest.yaml` and registers with the registry
2. A background task periodically discovers `market-data-service` instances
3. The readiness probe returns "ready" only after dependencies are discovered
4. On shutdown (SIGTERM/SIGINT), the service automatically deregisters

## SDK Usage Patterns

### Auto-Registration with Context Manager

```python
async with RegistryClient.from_manifest(
    manifest_path="manifest.yaml",
    instance_id="my-service-001",
    address="10.0.1.50",
    port=8080,
) as client:
    # Service is registered
    instances = await client.discover("dependency-service")
# Service is automatically deregistered
```

### Manual Registration

```python
config = RegistryClientConfig(host="registry", port=8080)

async with RegistryClient(config) as client:
    # Register
    result = await client.register(ServiceRegistration(
        name="my-service",
        version="1.0.0",
        instance_id="my-service-001",
        address="10.0.1.50",
        port=8080,
    ))

    # Use the service...

    # Deregister
    await client.deregister(
        instance_id="my-service-001",
        service_name="my-service",
        version="1.0.0",
    )
```

### Discovering Services

```python
# Find all healthy instances
instances = await client.discover("market-data-service")

# With version constraint
instances = await client.discover(
    "market-data-service",
    version="^1.0.0",
    healthy_only=True,
)

# Use the first instance
if instances:
    endpoint = instances[0].endpoint
    # Make request to endpoint...
```
