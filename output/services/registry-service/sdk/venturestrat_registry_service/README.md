# VentureStrat registry-service SDK

Python SDK for the VentureStrat registry-service service.

## Installation

```bash
pip install venturestrat_registry_service
```

For async support:

```bash
pip install venturestrat_registry_service[async]
```

For development:

```bash
pip install venturestrat_registry_service[dev]
```

## Quick Start

### Synchronous Client

```python
from venturestrat_registry_service import RegistryServiceClient

# Basic usage
with RegistryServiceClient(host="localhost", port=50051) as client:
    # Check service health
    healthy = client.health_check()
    print(f"Service healthy: {healthy}")

    # Make service calls
    # response = client.some_method(request)
```

### Asynchronous Client

```python
import asyncio
from venturestrat_registry_service import AsyncRegistryServiceClient

async def main():
    async with AsyncRegistryServiceClient(host="localhost", port=50051) as client:
        # Check service health
        healthy = await client.health_check()
        print(f"Service healthy: {healthy}")

        # Make async service calls
        # response = await client.some_method(request)

asyncio.run(main())
```

## Configuration

### Environment Variables

Set environment variables with the `REGISTRY_SERVICE_` prefix:

```bash
export REGISTRY_SERVICE_HOST=api.example.com
export REGISTRY_SERVICE_PORT=443
export REGISTRY_SERVICE_SECURE=true
export REGISTRY_SERVICE_AUTH_API_KEY=your-api-key
```

### Configuration File

```python
from venturestrat_registry_service import RegistryServiceConfig, RegistryServiceClient

# Load from environment
config = RegistryServiceConfig.from_env()

# Or load from file
config = RegistryServiceConfig.from_file("config.yaml")

# Create client with config
client = RegistryServiceClient.from_config(config)
```

### Configuration Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `host` | `REGISTRY_SERVICE_HOST` | `localhost` | Service host |
| `port` | `REGISTRY_SERVICE_PORT` | `50051` | Service port |
| `secure` | `REGISTRY_SERVICE_SECURE` | `false` | Use TLS |
| `timeout` | `REGISTRY_SERVICE_TIMEOUT` | `30.0` | Request timeout |
| `auth_api_key` | `REGISTRY_SERVICE_AUTH_API_KEY` | `null` | API key |
| `auth_token` | `REGISTRY_SERVICE_AUTH_TOKEN` | `null` | Bearer token |
| `debug` | `REGISTRY_SERVICE_DEBUG` | `false` | Debug logging |

## Authentication

### API Key Authentication

```python
from venturestrat_registry_service import RegistryServiceClient
from venturestrat_registry_service.auth import ApiKeyAuthProvider

auth = ApiKeyAuthProvider("your-api-key")
client = RegistryServiceClient(
    host="api.example.com",
    port=443,
    secure=True,
    auth=auth
)
```

### Bearer Token Authentication

```python
from venturestrat_registry_service import RegistryServiceClient
from venturestrat_registry_service.auth import TokenAuthProvider

auth = TokenAuthProvider("your-bearer-token")
client = RegistryServiceClient(
    host="api.example.com",
    port=443,
    secure=True,
    auth=auth
)
```

### Basic Authentication

```python
from venturestrat_registry_service import RegistryServiceClient
from venturestrat_registry_service.auth import BasicAuthProvider

auth = BasicAuthProvider("username", "password")
client = RegistryServiceClient(
    host="api.example.com",
    port=443,
    secure=True,
    auth=auth
)
```

## Error Handling

The SDK provides specific exceptions for different error conditions:

```python
from venturestrat_registry_service import (
    RegistryServiceClient,
    RegistryServiceError,
    RegistryServiceConnectionError,
    RegistryServiceValidationError,
    RegistryServiceNotFoundError,
)

try:
    with RegistryServiceClient() as client:
        # response = client.some_method(request)
        pass
except RegistryServiceValidationError as e:
    print(f"Validation error: {e}")
except RegistryServiceNotFoundError as e:
    print(f"Resource not found: {e}")
except RegistryServiceConnectionError as e:
    print(f"Connection error: {e}")
except RegistryServiceError as e:
    print(f"Service error: {e}")
```

## Models

The SDK includes Pydantic models that correspond to the service's protobuf messages:

```python
from venturestrat_registry_service.models import ExampleRequest, ExampleResponse

# Create request
request = ExampleRequest(
    id="example-123",
    name="Example Name",
    tags=["tag1", "tag2"]
)

# Validate and serialize
json_data = request.model_dump_json()
```

## Examples

See the `examples/` directory for more complete examples:

- `examples/basic_usage.py` - Basic synchronous client usage
- `examples/async_usage.py` - Asynchronous client usage

## Development

### Running Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy venturestrat_registry_service/
```

### Linting

```bash
ruff check venturestrat_registry_service/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://docs.venturestrat.com
- Issues: https://github.com/venturestrat/venturestrat/issues
- Discussions: https://github.com/venturestrat/venturestrat/discussions
