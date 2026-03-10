# VentureStrat API Gateway

Kong-based API Gateway providing unified entry point for all VentureStrat services with Consul service discovery, dual authentication (API keys + JWT), Redis-backed rate limiting, and gRPC-Web support for browser clients.

## Overview

The VentureStrat API Gateway serves as the single entry point for external clients and provides:

- **Service Discovery**: Automatic routing via Consul service registry with health-aware load balancing
- **Authentication**: API keys for external clients, JWT tokens for service-to-service communication
- **Rate Limiting**: Redis-backed rate limiting with configurable consumer tiers (free, standard, premium)
- **Observability**: Request tracing, Prometheus metrics, and structured JSON logging
- **gRPC-Web**: Browser-compatible gRPC transcoding with CORS support
- **High Availability**: Health checks, failover, and circuit breaking

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KONG GATEWAY (DB-less)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Routing    │  │   API Key    │  │     JWT      │  │ Rate Limit   │        │
│  │   (Consul)   │  │    Auth      │  │    Auth      │  │   (Redis)    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  gRPC-Web    │  │   Logging    │  │   Metrics    │  │    CORS      │        │
│  │ Transcoding  │  │ (Correlation)│  │ (Prometheus) │  │   Support    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
         │                                                        │
         ▼                                                        ▼
┌─────────────────────┐                                ┌─────────────────────┐
│       CONSUL        │◄──────────────────────────────►│       REDIS         │
│  Service Discovery  │                                │   Rate Limit Store  │
│    Health Checks    │                                │   Session Storage   │
└─────────────────────┘                                └─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND SERVICES                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │ registry-service│  │ pricing-service │  │  risk-service   │                 │
│  │    :8080/REST   │  │    :8090/REST   │  │   :8100/REST    │                 │
│  │   :50051/gRPC   │  │   :50052/gRPC   │  │   :50053/gRPC   │                 │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Consul and Redis running (from `docker-compose.infra.yaml`)

### Start Gateway

```bash
# 1. Start infrastructure services first
docker compose -f docker-compose.infra.yaml up -d

# 2. Verify infrastructure is healthy
curl http://localhost:8500/v1/status/leader  # Consul
redis-cli -h localhost -p 6379 ping          # Redis

# 3. Start gateway services
docker compose -f gateway/docker-compose.gateway.yaml up -d

# 4. Wait for gateway to be healthy (may take 30-60 seconds)
curl http://localhost:8000/health

# 5. Verify gateway admin API (development only)
curl http://localhost:8001/status
```

### Test API Access

```bash
# Test with API key (external client pattern)
curl -H "X-API-Key: dev-api-key-12345" \
     -H "Accept: application/json" \
     http://localhost:8000/api/v1/registry/services

# Get JWT token for service-to-service communication
curl -X POST http://localhost:8002/token \
     -H "Content-Type: application/json" \
     -d '{"service_name": "test-service"}'

# Example response:
# {
#   "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "Bearer",
#   "expires_at": "2026-01-05T11:30:00Z",
#   "expires_in": 3600
# }

# Use JWT token for service-to-service calls
TOKEN=$(curl -s -X POST http://localhost:8002/token \
  -H "Content-Type: application/json" \
  -d '{"service_name": "my-service"}' | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" \
     -H "Accept: application/json" \
     http://localhost:8000/api/v1/registry/services
```

## Configuration

### Kong Configuration (`kong.yaml`)

The declarative configuration defines:

- **Upstreams**: Load balancing groups with health checks and Consul DNS targets
- **Services**: Backend service definitions with timeouts and retries
- **Routes**: Path-based routing rules with priority and protocols
- **Plugins**: Authentication, rate limiting, logging, metrics, CORS
- **Consumers**: API key and JWT credential management

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `dev-secret-change-in-prod` | JWT signing secret (CHANGE IN PRODUCTION) |
| `KONG_DNS_RESOLVER` | `consul-server-1:8600` | Consul DNS server for service discovery |
| `KONG_LOG_LEVEL` | `info` | Kong logging level (debug, info, notice, warn, error) |
| `KONG_WORKER_PROCESSES` | `auto` | Number of Kong worker processes |
| `KONG_PROXY_ACCESS_LOG_FORMAT` | JSON | Structured logging format |

### Rate Limiting Configuration

Rate limits are enforced per consumer tier:

| Consumer Tier | Minute Limit | Hour Limit | Daily Limit | Use Case |
|---------------|--------------|------------|-------------|----------|
| Global (default) | 1,000 | 10,000 | - | Fallback limit |
| Free | 100 | 1,000 | 2,500 | External developers |
| Standard | 1,000 | 10,000 | 50,000 | Paid API users |
| Premium | 5,000 | 100,000 | 500,000 | Enterprise clients |

## API Endpoints

### Gateway Management Endpoints

| Method | Path | Description | Authentication |
|--------|------|-------------|----------------|
| GET | `/health` | Gateway health check | None |
| GET | `/metrics` (admin) | Prometheus metrics | Admin API only |
| GET | `:8001/status` | Kong status and configuration | Admin API only |
| GET | `:8001/services` | List configured services | Admin API only |

### JWT Issuer Service Endpoints

| Method | Path | Description | Request Body |
|--------|------|-------------|--------------|
| POST | `/api/v1/auth/token` | Issue JWT token | `{"service_name": "string", "scope": "optional"}` |
| POST | `/validate` (test only) | Validate JWT token | `{"token": "jwt_string"}` |
| GET | `/health` | Health check | - |

### Proxied Backend Services

| Gateway Path | Backend Service | Protocol | Description |
|--------------|-----------------|----------|-------------|
| `/api/v1/registry/*` | registry-service:8080 | REST | Service registry operations |
| `/grpc/v1/registry/*` | registry-service:50051 | gRPC-Web | Browser-compatible gRPC |

## Authentication & Authorization

### API Key Authentication (External Clients)

External clients authenticate with API keys in headers or query parameters:

```bash
# Header authentication (recommended)
curl -H "X-API-Key: dev-api-key-12345" \
     http://localhost:8000/api/v1/registry/services

# Query parameter authentication
curl "http://localhost:8000/api/v1/registry/services?apikey=dev-api-key-12345"

# Multiple header names supported
curl -H "apikey: dev-api-key-12345" \
     http://localhost:8000/api/v1/registry/services
```

**Pre-configured API Keys:**

| Key | Consumer Tier | Rate Limits | Use Case |
|-----|---------------|-------------|----------|
| `dev-api-key-12345` | Default | 1000/min, 10000/hr | Development testing |
| `test-api-key-67890` | Test | 1000/min, 10000/hr | Integration testing |
| `free-api-key-11111` | Free | 100/min, 1000/hr | Free tier users |
| `standard-api-key-22222` | Standard | 1000/min, 10000/hr | Paid tier users |
| `premium-api-key-33333` | Premium | 5000/min, 100000/hr | Enterprise users |

### JWT Token Authentication (Service-to-Service)

Internal services use JWT tokens for authentication:

```bash
# Step 1: Request a JWT token
curl -X POST http://localhost:8002/token \
     -H "Content-Type: application/json" \
     -d '{
       "service_name": "pricing-service",
       "scope": "read:quotes write:quotes"
     }'

# Example response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwcmljaW5nLXNlcnZpY2UiLCJpc3MiOiJ0cmVhc3VyeW9zLWdhdGV3YXkiLCJhdWQiOiJ0cmVhc3VyeW9zLXNlcnZpY2VzIiwiZXhwIjoxNzM2MDc2NjAwLCJpYXQiOjE3MzYwNzMwMDAsImp0aSI6IjEyMzRhYmNkLWVmNTYtNzg5MC1hYmNkLWVmMTIzNDU2Nzg5MCIsInR5cCI6ImFjY2Vzc190b2tlbiIsInNjb3BlIjoicmVhZDpxdW90ZXMgd3JpdGU6cXVvdGVzIn0.signature",
  "token_type": "Bearer",
  "expires_at": "2026-01-05T11:30:00Z",
  "expires_in": 3600
}

# Step 2: Use token for service calls
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/registry/services
```

**JWT Token Claims:**
- `sub`: Service name (e.g., "pricing-service")
- `iss`: Issuer ("venturestrat-gateway")
- `aud`: Audience ("venturestrat-services")
- `exp`: Expiration timestamp (Unix)
- `iat`: Issued at timestamp (Unix)
- `jti`: Unique token ID (UUID)
- `typ`: Token type ("access_token")
- `scope`: Optional permissions scope

### Authentication Error Responses

```bash
# No authentication (401 Unauthorized)
curl http://localhost:8000/api/v1/registry/services
# Response: {"message": "No API key found in request", "error": "Unauthorized"}

# Invalid API key (403 Forbidden)
curl -H "X-API-Key: invalid-key" http://localhost:8000/api/v1/registry/services
# Response: {"message": "Invalid authentication credentials", "error": "Forbidden"}

# Expired JWT token (401 Unauthorized)
curl -H "Authorization: Bearer expired_token" http://localhost:8000/api/v1/registry/services
# Response: {"message": "Token has expired", "error": "Unauthorized"}
```

## Rate Limiting

Rate limits are enforced per consumer with Redis-backed storage:

### Rate Limit Headers

All responses include rate limit information:

```bash
curl -I -H "X-API-Key: free-api-key-11111" \
     http://localhost:8000/api/v1/registry/services

# Response headers:
HTTP/1.1 200 OK
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 99
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Hour: 999
RateLimit-Reset: 1736073060
```

### Rate Limit Exceeded (429)

```bash
# After exceeding rate limit:
curl -H "X-API-Key: free-api-key-11111" \
     http://localhost:8000/api/v1/registry/services

# Response:
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 0

{
  "message": "API rate limit exceeded",
  "error": "Too Many Requests"
}
```

### Testing Rate Limits

```bash
# Test free tier rate limits (100/minute)
for i in {1..105}; do
  echo "Request $i:"
  curl -s -o /dev/null -w "%{http_code}" \
       -H "X-API-Key: free-api-key-11111" \
       http://localhost:8000/api/v1/registry/services
  echo
  sleep 0.5
done
# Requests 101-105 should return 429
```

## gRPC-Web Support

Browser clients can access gRPC services via gRPC-Web transcoding:

### gRPC-Web Example (JavaScript)

```javascript
// Install: npm install grpc-web google-protobuf

import {RegistryServiceClient} from './generated/registry_grpc_web_pb';
import {DiscoverServiceRequest} from './generated/registry_pb';

// Create client pointing to gateway
const client = new RegistryServiceClient('http://localhost:8000', null, null);

// Set up metadata with API key
const metadata = {
  'X-API-Key': 'dev-api-key-12345'
};

// Create request
const request = new DiscoverServiceRequest();
request.setName('pricing-service');

// Make gRPC-Web call
client.discoverService(request, metadata, (err, response) => {
  if (err) {
    console.error('gRPC-Web error:', err);
    return;
  }

  console.log('Services found:', response.getServicesList());
});
```

### gRPC-Web with curl (Testing)

```bash
# Test gRPC-Web endpoint (requires protobuf data)
curl -X POST http://localhost:8000/grpc/v1/registry/DiscoverService \
     -H "Content-Type: application/grpc-web+proto" \
     -H "X-API-Key: dev-api-key-12345" \
     -H "X-Grpc-Web: 1" \
     --data-binary @discover_request.pb

# CORS preflight check
curl -X OPTIONS http://localhost:8000/grpc/v1/registry/DiscoverService \
     -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-API-Key,Content-Type"
```

## Observability

### Request Tracing

All requests include correlation IDs for distributed tracing:

```bash
# Provide correlation ID
curl -H "X-API-Key: dev-api-key-12345" \
     -H "X-Correlation-ID: my-trace-123" \
     http://localhost:8000/api/v1/registry/services

# Auto-generated correlation ID
curl -H "X-API-Key: dev-api-key-12345" \
     http://localhost:8000/api/v1/registry/services

# Response includes correlation ID:
# X-Correlation-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Prometheus Metrics

Metrics are available at the admin API (port 8001):

```bash
# Scrape metrics (Prometheus format)
curl http://localhost:8001/metrics

# Key metrics include:
# - kong_http_requests_total{service,consumer,status}
# - kong_latency{type="request|upstream"}
# - kong_bandwidth{type="ingress|egress"}
# - kong_nginx_http_current_connections
```

**Example Metrics:**
```prometheus
# Request counts by service and status
kong_http_requests_total{service="registry-service",consumer="dev",status="200"} 42

# Response latencies
kong_latency_bucket{type="request",service="registry-service",le="100"} 38
kong_latency_bucket{type="upstream",service="registry-service",le="50"} 40

# Rate limit metrics
kong_rate_limiting_limit{service="registry-service",consumer="free-tier"} 100
kong_rate_limiting_usage{service="registry-service",consumer="free-tier"} 67
```

### Structured Logging

Kong outputs structured JSON logs for easy parsing:

```json
{
  "timestamp": "2026-01-05T10:30:45.123Z",
  "client_ip": "172.18.0.1",
  "method": "GET",
  "uri": "/api/v1/registry/services",
  "status": "200",
  "size": "1234",
  "response_time": "0.045",
  "upstream_time": "0.032",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "consumer": "dev-consumer",
  "service_name": "registry-service",
  "route_name": "registry-rest",
  "auth_method": "api-key"
}
```

### Log Analysis Examples

```bash
# Follow gateway logs
docker logs -f kong-gateway

# Filter by status code
docker logs kong-gateway | jq 'select(.status == "500")'

# Extract response times
docker logs kong-gateway | jq -r '.response_time' | grep -v null

# Group by consumer
docker logs kong-gateway | jq -r '.consumer' | sort | uniq -c

# Track errors by service
docker logs kong-gateway | jq 'select(.status >= "400") | {service: .service_name, status: .status, uri: .uri}'
```

## Testing

### Unit Tests

```bash
cd gateway
pip install -r requirements-test.txt

# Run unit tests
pytest tests/unit -v

# Test specific components
pytest tests/unit/test_kong_config.py -v
pytest tests/unit/test_jwt_issuer.py -v
```

### Integration Tests

Integration tests require Docker infrastructure:

```bash
# Start infrastructure first
docker compose -f docker-compose.infra.yaml up -d

# Run integration tests
INTEGRATION_TESTS=1 pytest tests/integration -v

# Test specific areas
INTEGRATION_TESTS=1 pytest tests/integration/test_api_key_auth.py -v
INTEGRATION_TESTS=1 pytest tests/integration/test_rate_limiting.py -v
INTEGRATION_TESTS=1 pytest tests/integration/test_grpc_web.py -v
```

### End-to-End Tests

```bash
# Full stack testing
INTEGRATION_TESTS=1 pytest tests/e2e -v

# Test with verbose output
INTEGRATION_TESTS=1 pytest tests/e2e -v -s
```

### Manual Testing Scripts

```bash
# Test API key authentication flows
python gateway/tests/manual/verify_test_consumers.py

# Test service discovery and registration
python gateway/tests/manual/verify_service_registration.py

# Test health-based traffic routing
python gateway/tests/manual/task_4_4_verify_healthy_instances_traffic.py
```

## Development

### Local Development Setup

```bash
# 1. Start infrastructure
docker compose -f docker-compose.infra.yaml up -d

# 2. Verify infrastructure health
curl http://localhost:8500/v1/status/leader
redis-cli ping

# 3. Start gateway in development mode (with logs)
docker compose -f gateway/docker-compose.gateway.yaml up

# 4. In another terminal, make configuration changes
# Edit gateway/kong.yaml

# 5. Restart Kong to reload configuration
docker compose -f gateway/docker-compose.gateway.yaml restart kong

# 6. Verify configuration
curl http://localhost:8001/config | jq .
```

### Adding New Services

1. **Register service with Consul:**
```bash
curl -X PUT http://localhost:8500/v1/agent/service/register \
     -H "Content-Type: application/json" \
     -d '{
       "ID": "pricing-service-1",
       "Name": "pricing-service",
       "Address": "pricing-service",
       "Port": 8090,
       "Check": {
         "HTTP": "http://pricing-service:8090/health/ready",
         "Interval": "10s"
       }
     }'
```

2. **Add upstream to `kong.yaml`:**
```yaml
upstreams:
  - name: pricing-service.upstream
    algorithm: round-robin
    healthchecks:
      active:
        type: http
        http_path: /health/ready
    targets:
      - target: pricing-service.service.consul:8090
        weight: 100
```

3. **Add service and route:**
```yaml
services:
  - name: pricing-service
    host: pricing-service.upstream
    port: 80
    protocol: http
    routes:
      - name: pricing-rest
        paths:
          - /api/v1/pricing
        strip_path: true
        protocols: [http, https]
```

4. **Restart Kong:**
```bash
docker compose restart kong
```

### Adding Custom Plugins

```bash
# 1. Create plugin directory
mkdir -p gateway/plugins/custom/my-plugin

# 2. Create plugin handler
cat > gateway/plugins/custom/my-plugin/handler.lua << 'EOF'
local MyPluginHandler = {
  PRIORITY = 1000,
  VERSION = "1.0.0",
}

function MyPluginHandler:access(conf)
  -- Plugin logic here
  kong.log.info("Custom plugin executed")
end

return MyPluginHandler
EOF

# 3. Create plugin schema
cat > gateway/plugins/custom/my-plugin/schema.lua << 'EOF'
return {
  name = "my-plugin",
  fields = {
    { config = {
        type = "record",
        fields = {
          { my_option = { type = "string", default = "default_value" } },
        },
      },
    },
  },
}
EOF

# 4. Update docker-compose to load custom plugins
# Add to kong environment:
# KONG_PLUGINS: bundled,my-plugin
# KONG_LUA_PACKAGE_PATH: /kong/plugins/custom/?.lua;;

# 5. Restart Kong
docker compose restart kong
```

## Production Considerations

### Security

**Essential Production Changes:**

```bash
# 1. Change JWT secret
export JWT_SECRET="$(openssl rand -base64 64)"

# 2. Restrict admin API access (remove port exposure in production)
# Comment out in docker-compose.yaml:
# - "8001:8001"   # Admin API

# 3. Use proper TLS certificates
# Place certificates in gateway/certs/:
# - server.crt
# - server.key

# 4. Configure trusted IPs
# Update kong.yaml or environment:
KONG_TRUSTED_IPS="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

# 5. Review CORS origins
# Update kong.yaml cors plugin:
origins:
  - "https://app.venturestrat.io"
  - "https://admin.venturestrat.io"
```

### Performance Tuning

```bash
# 1. Scale Kong horizontally
docker compose up --scale kong=3

# 2. Tune worker processes
KONG_WORKER_PROCESSES=auto  # or specific number

# 3. Configure upstream keepalive
KONG_UPSTREAM_KEEPALIVE_POOL_SIZE=60
KONG_UPSTREAM_KEEPALIVE_MAX_REQUESTS=100
KONG_UPSTREAM_KEEPALIVE_IDLE_TIMEOUT=60

# 4. Optimize Redis connection
# Use Redis Cluster for high availability

# 5. Configure rate limit settings per workload
# Adjust rate limits based on actual usage patterns
```

### Monitoring & Alerting

```bash
# 1. Set up Grafana dashboards for Kong metrics
# Import Kong dashboard ID: 7424

# 2. Configure alerting rules
# High error rate: rate(kong_http_requests_total{status=~"5.."}[5m]) > 0.1
# High latency: histogram_quantile(0.95, kong_latency_bucket{type="request"}) > 1000

# 3. Monitor upstream service health
curl http://localhost:8001/upstreams/registry-service.upstream/health

# 4. Track rate limit violations
# Alert on: increase(kong_rate_limiting_limit_exceeded_total[5m]) > 10
```

### High Availability Setup

```yaml
# Production docker-compose with multiple Kong instances
services:
  kong-1:
    image: kong:3.5
    # ... kong config ...

  kong-2:
    image: kong:3.5
    # ... kong config ...

  kong-lb:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - kong-1
      - kong-2
```

## Troubleshooting

### Common Issues

**Kong fails to start:**

```bash
# Check Consul connectivity
curl http://localhost:8500/v1/status/leader

# Validate kong.yaml syntax
docker run --rm -v $(pwd)/gateway/kong.yaml:/kong.yaml kong:3.5 kong config parse /kong.yaml

# Check Docker logs
docker logs kong-gateway

# Common fixes:
# 1. Ensure Consul is running and healthy
# 2. Check network connectivity (venturestrat-network)
# 3. Verify Redis is accessible
```

**Service not routable:**

```bash
# 1. Check service registration in Consul
curl http://localhost:8500/v1/catalog/service/registry-service

# 2. Check upstream health in Kong
curl http://localhost:8001/upstreams/registry-service.upstream/health

# 3. Validate route configuration
curl http://localhost:8001/routes | jq '.data[] | select(.name=="registry-rest")'

# 4. Test direct service connectivity
curl http://registry-service:8080/health/ready
```

**Rate limiting not working:**

```bash
# 1. Check Redis connectivity
redis-cli -h localhost -p 6379 ping

# 2. Verify consumer configuration
curl http://localhost:8001/consumers/free-tier-consumer

# 3. Check plugin configuration
curl http://localhost:8001/plugins | jq '.data[] | select(.name=="rate-limiting")'

# 4. Test rate limiting directly
for i in {1..10}; do curl -H "X-API-Key: free-api-key-11111" http://localhost:8000/api/v1/registry/services; done
```

**JWT validation failing:**

```bash
# 1. Check JWT issuer health
curl http://localhost:8002/health

# 2. Validate token format
curl -X POST http://localhost:8002/validate \
     -H "Content-Type: application/json" \
     -d '{"token": "your_jwt_token_here"}'

# 3. Check JWT secret configuration
# Ensure JWT_SECRET matches between kong.yaml and jwt-issuer

# 4. Verify token hasn't expired
# JWT tokens expire in 1 hour by default
```

**Service discovery issues:**

```bash
# 1. Check Consul DNS resolution from Kong
docker exec kong-gateway nslookup registry-service.service.consul

# 2. Verify service registration in Consul
curl http://localhost:8500/v1/health/service/registry-service

# 3. Check Kong upstream configuration against Consul services
curl http://localhost:8001/upstreams | jq '.data[] | .name'
curl http://localhost:8500/v1/catalog/services | jq 'keys[]'

# 4. Test DNS resolution for specific service
docker exec kong-gateway nslookup schema-registry-service.service.consul
docker exec kong-gateway ping -c 1 schema-registry-service.service.consul

# 5. Check if services are healthy in Consul
curl "http://localhost:8500/v1/health/service/registry-service?passing=true" | jq '.[].Service'
```

**Kong Admin API connectivity issues:**

```bash
# 1. Verify Kong Admin API is accessible
curl -f http://localhost:8001/status || echo "Kong Admin API not reachable"

# 2. Check if Kong is running in database-less mode
curl http://localhost:8001/status | jq '.configuration | {mode: .database, postgres: .pg_database}'

# 3. For database-less mode, verify kong.yaml changes are loaded
docker exec kong-gateway kong config parse /etc/kong/kong.yaml

# 4. Check Kong worker processes
docker exec kong-gateway ps aux | grep kong
```

### Debug Commands

```bash
# Kong status and configuration
curl http://localhost:8001/status | jq .

# List all services
curl http://localhost:8001/services | jq '.data[] | {name: .name, host: .host, port: .port}'

# List all routes
curl http://localhost:8001/routes | jq '.data[] | {name: .name, paths: .paths, service: .service.name}'

# Check upstream health
curl http://localhost:8001/upstreams | jq '.data[] | .name'
curl http://localhost:8001/upstreams/registry-service.upstream/health | jq .

# List consumers
curl http://localhost:8001/consumers | jq '.data[] | {username: .username, custom_id: .custom_id}'

# Check plugin configuration
curl http://localhost:8001/plugins | jq '.data[] | {name: .name, service: .service?.name, enabled: .enabled}'

# Test service connectivity
curl -v http://localhost:8000/api/v1/registry/services \
     -H "X-API-Key: dev-api-key-12345"
```

### Performance Debugging

```bash
# Monitor request latencies
curl http://localhost:8001/metrics | grep kong_latency

# Check connection pools
curl http://localhost:8001/status | jq '.database.reachable'

# Monitor rate limit usage
curl http://localhost:8001/metrics | grep kong_rate_limiting

# Test load balancing
for i in {1..10}; do
  curl -H "X-API-Key: dev-api-key-12345" \
       http://localhost:8000/api/v1/registry/services \
       -w "Response time: %{time_total}s\n" -o /dev/null -s
done
```

### Log Analysis

```bash
# Real-time log monitoring
docker logs -f kong-gateway | jq .

# Filter by error status
docker logs kong-gateway | jq 'select(.status >= "400")'

# Extract slow requests (>1s)
docker logs kong-gateway | jq 'select(.response_time and (.response_time | tonumber) > 1.0)'

# Group by consumer
docker logs kong-gateway | jq -r '.consumer // "anonymous"' | sort | uniq -c | sort -nr

# Track authentication failures
docker logs kong-gateway | jq 'select(.status == "401" or .status == "403") | {time: .timestamp, uri: .uri, status: .status, consumer: .consumer}'

# Monitor rate limit hits
docker logs kong-gateway | jq 'select(.status == "429") | {time: .timestamp, consumer: .consumer, uri: .uri}'
```

## Support

For issues and questions:

- **Documentation**: This README and inline code comments
- **Logs**: `docker logs kong-gateway`, `docker logs jwt-issuer`
- **Admin API**: http://localhost:8001 (development only)
- **Health Checks**: http://localhost:8000/health
- **Metrics**: http://localhost:8001/metrics (Prometheus format)

For production deployments, ensure proper security hardening, monitoring, and backup procedures are in place.
