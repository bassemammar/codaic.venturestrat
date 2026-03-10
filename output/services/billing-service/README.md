# Billing Service

VentureStrat billing-service

## Development

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- VentureStrat CLI (`venturestrat`)

### Local Development

1. **Start the development environment:**
   ```bash
   venturestrat dev up billing-service
   ```

2. **The service will be available at:**
   - HTTP API: http://localhost:8063
   - API Documentation: http://localhost:8063/docs

3. **Health checks:**
   - Liveness: http://localhost:8063/health/live
   - Readiness: http://localhost:8063/health/ready

### Running Tests

```bash
# Run all tests
venturestrat test billing-service

# Run specific test types
venturestrat test billing-service --markers unit
venturestrat test billing-service --markers integration

# Run with quality gates
venturestrat test billing-service --gates
```

### Code Generation

## API

### REST Endpoints

- `GET /api/v1/billing_service` - List billing_service items
- `POST /api/v1/billing_service` - Create new item
- `GET /api/v1/billing_service/{id}` - Get item by ID
- `PUT /api/v1/billing_service/{id}` - Update item
- `DELETE /api/v1/billing_service/{id}` - Delete item

### Health Endpoints

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe


## Configuration

Configuration is managed through environment variables and Pydantic settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | billing-service | Service name for registry |
| `SERVICE_VERSION` | 1.0.0 | Service version |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8063 | HTTP server port |
| `LOG_LEVEL` | INFO | Logging level |
| `CONSUL_HOST` | localhost | Consul server host |
| `CONSUL_PORT` | 8500 | Consul server port |

## Architecture

```
billing-service/
├── src/billing_service/          # Source code
│   ├── main.py                     # FastAPI application entry point
│   ├── config.py                   # Configuration management
│   ├── api/                        # REST API endpoints
│   │   ├── __init__.py
│   │   ├── billing_service.py          # Main API routes
│   │   └── models.py               # API request/response models
│   ├── models.py                   # Domain models
│   └── health.py                   # Health check endpoints
├── tests/                          # Test suite
│   ├── unit/                       # Unit tests
│   └── integration/                # Integration tests
├── migrations/                     # Database migrations
└── manifest.yaml                   # Service manifest
```

## Dependencies



## Development Notes

- Hot reload is enabled in development mode
- Service automatically registers with Consul on startup
- Logs are structured JSON for observability
- Health checks follow Kubernetes standards
