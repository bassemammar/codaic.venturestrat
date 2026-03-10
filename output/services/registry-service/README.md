# VentureStrat Registry Service

Service Registry and Discovery for the VentureStrat platform. This service provides Consul-based service registration, discovery, and health monitoring.

## Features

- **Service Registration**: Services register themselves with metadata and health checks
- **Service Discovery**: Query for healthy service instances by name, version, and tags
- **Health Monitoring**: Automatic health checking with configurable thresholds
- **Event Publishing**: Service lifecycle events published to Kafka
- **Manifest Support**: Parse and validate `manifest.yaml` files

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+

### Start Development Stack

```bash
# Start all infrastructure (Consul, Kafka, PostgreSQL)
docker-compose -f docker-compose.dev.yaml up -d

# View logs
docker-compose -f docker-compose.dev.yaml logs -f registry-service
```

### Access Services

| Service | URL |
|---------|-----|
| Registry API | http://localhost:8080 |
| Consul UI | http://localhost:8500 |
| Kafka UI | http://localhost:8090 |
| OpenAPI Docs | http://localhost:8080/docs |

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/unit -v

# Run integration tests (requires Docker stack running)
pytest tests/integration -v -m integration
```

## API Overview

### Registration

```bash
# Register a service
curl -X POST http://localhost:8080/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-service",
    "version": "1.0.0",
    "address": "10.0.1.50",
    "port": 8080,
    "protocol": "http"
  }'

# Deregister
curl -X DELETE http://localhost:8080/api/v1/services/{instance_id}
```

### Discovery

```bash
# Find all instances of a service
curl http://localhost:8080/api/v1/services/my-service

# Filter by version
curl "http://localhost:8080/api/v1/services/my-service?version=^1.0.0"

# List all services
curl http://localhost:8080/api/v1/services
```

### Health

```bash
# Get service health overview
curl http://localhost:8080/health/services

# Get specific service health
curl http://localhost:8080/health/services/my-service
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CONSUL_HOST` | localhost | Consul server hostname |
| `CONSUL_PORT` | 8500 | Consul HTTP port |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 | Kafka broker addresses |
| `DATABASE_URL` | - | PostgreSQL connection URL |
| `LOG_LEVEL` | INFO | Logging level |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Registry Service                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  REST API   │  │  gRPC API   │  │  Event Pub  │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         └────────────────┴────────────────┘                  │
│                          │                                   │
│              ┌───────────▼───────────┐                       │
│              │   Registry Core       │                       │
│              │  - Manifest Parser    │                       │
│              │  - Health Manager     │                       │
│              │  - Discovery Engine   │                       │
│              └───────────┬───────────┘                       │
└──────────────────────────┼───────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Consul  │    │  Kafka   │    │ Postgres │
    └──────────┘    └──────────┘    └──────────┘
```

## Development

### Project Structure

```
services/registry-service/
├── src/registry/          # Source code
│   ├── api/              # REST/gRPC endpoints
│   ├── core/             # Business logic
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── charts/               # Helm charts
├── migrations/           # SQL migrations
├── Dockerfile            # Container build
└── docker-compose.dev.yaml
```

### Adding a New Endpoint

1. Define the route in `src/registry/api/`
2. Add tests in `tests/unit/` and `tests/integration/`
3. Update OpenAPI documentation

## Troubleshooting

### Common Issues

#### Service Startup Failures

**Symptom**: Service fails to start or crashes immediately
```bash
docker logs registry-service
# Error: Could not connect to Consul at localhost:8500
```

**Cause**: Consul not running or not accessible

**Solution**:
```bash
# Check if Consul is running
docker ps | grep consul

# Start Consul if not running
docker-compose -f docker-compose.dev.yaml up -d consul

# Check Consul health
curl http://localhost:8500/v1/status/leader

# Verify network connectivity
docker network ls
docker inspect $(docker-compose -f docker-compose.dev.yaml ps -q consul)
```

#### Service Registration Failures

**Symptom**: Services fail to register with error messages like "Connection refused" or "Service registration failed"
```bash
curl -X POST http://localhost:8080/api/v1/services -d '...'
# {"error": "Service registration failed: connection refused"}
```

**Cause**: Registry service cannot connect to Consul backend

**Solution**:
```bash
# Check Consul connectivity from registry service
docker exec registry-service curl http://consul:8500/v1/status/peers

# Verify Consul cluster status
curl http://localhost:8500/v1/status/peers

# Check registry service logs for connection errors
docker logs registry-service | grep -i consul
```

#### Database Connection Issues

**Symptom**: Service starts but fails on database operations
```bash
# Error: could not connect to database
# psycopg2.OperationalError: could not connect to server
```

**Cause**: PostgreSQL not accessible or credentials incorrect

**Solution**:
```bash
# Check PostgreSQL container status
docker ps | grep postgres

# Test database connection
docker exec registry-service pg_isready -h postgres -p 5432

# Verify DATABASE_URL environment variable
docker exec registry-service env | grep DATABASE_URL

# Check database credentials in docker-compose
docker-compose -f docker-compose.dev.yaml config | grep -A 5 postgres
```

#### Service Discovery Returns Empty Results

**Symptom**: Discovery API returns no services even though services are registered
```bash
curl http://localhost:8080/api/v1/services/my-service
# {"instances": []}
```

**Cause**: Services registered in different Consul datacenter or health checks failing

**Solution**:
```bash
# Check services directly in Consul
curl http://localhost:8500/v1/catalog/services

# Verify service registration in Consul
curl http://localhost:8500/v1/health/service/my-service

# Check health check status
curl "http://localhost:8500/v1/health/checks/my-service"

# Verify datacenter configuration
curl http://localhost:8500/v1/catalog/datacenters
```

#### Kafka Event Publishing Failures

**Symptom**: Service registration works but events are not published
```bash
# Registry service logs show: "Failed to publish event to Kafka"
```

**Cause**: Kafka not accessible or topic doesn't exist

**Solution**:
```bash
# Check Kafka broker status
docker ps | grep kafka

# Test Kafka connectivity from registry service
docker exec registry-service nc -zv kafka 9092

# List Kafka topics
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check Kafka logs
docker logs kafka | grep -i error

# Verify KAFKA_BOOTSTRAP_SERVERS configuration
docker exec registry-service env | grep KAFKA_BOOTSTRAP_SERVERS
```

#### Port Binding Issues

**Symptom**: Service fails to start with "Address already in use" error
```bash
# Error: [Errno 98] Address already in use
```

**Cause**: Port 8080 already occupied by another service

**Solution**:
```bash
# Check what's using port 8080
lsof -i :8080
# or
netstat -tlnp | grep :8080

# Stop conflicting service or change registry service port
# Edit docker-compose.dev.yaml to use different port
docker-compose -f docker-compose.dev.yaml down
# Modify port mapping: "8081:8080" instead of "8080:8080"
docker-compose -f docker-compose.dev.yaml up -d
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Set debug logging level
export LOG_LEVEL=DEBUG

# Run with debug mode
docker-compose -f docker-compose.dev.yaml up -d
docker logs -f registry-service
```

### Health Check Commands

```bash
# Quick health check
curl http://localhost:8080/health

# Detailed service health
curl http://localhost:8080/health/services

# Check registry service status in Consul
curl http://localhost:8500/v1/health/service/registry-service

# Verify all infrastructure components
make doctor  # if available, or check each component:
curl http://localhost:8500/v1/status/leader    # Consul
docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092  # Kafka
docker exec postgres pg_isready               # PostgreSQL
```

### Performance Issues

**Symptom**: Slow response times or timeouts

**Solution**:
```bash
# Check resource usage
docker stats registry-service

# Monitor Consul performance
curl http://localhost:8500/v1/status/peers

# Check database connection pool
# Look for connection pool exhaustion in logs
docker logs registry-service | grep -i "connection pool"

# Enable PostgreSQL query logging for slow queries
# Add to docker-compose.dev.yaml postgres environment:
# POSTGRES_INITDB_ARGS: "-c log_statement=all -c log_min_duration_statement=1000"
```

## Deployment

### Kubernetes

```bash
# Install with Helm
helm install registry-service ./charts/registry-service \
  --namespace venturestrat \
  --set consul.host=consul-server
```

## License

MIT
