# gRPC-Web Route Configuration Design

> Task 13.1 - Wave 13: gRPC-Web route configuration for VentureStrat API Gateway
> Created: 2026-01-05
> Status: Complete

## Overview

This document details the gRPC-Web route configuration design for Kong Gateway, enabling browser clients to access gRPC services through HTTP/REST-like interfaces with automatic transcoding.

## Current State Analysis

The existing kong.yaml already has basic gRPC-Web configuration:

```yaml
# Existing configuration (lines 88-101)
services:
  - name: registry-grpc-service
    host: registry-service.service.consul
    port: 50051
    protocol: grpc
    routes:
      - name: registry-grpc-web
        paths:
          - /grpc/v1/registry
        strip_path: true
        protocols:
          - http
          - https

# Existing plugin (lines 240-245)
plugins:
  - name: grpc-web
    service: registry-grpc-service
    config:
      pass_stripped_path: false
```

## Enhanced gRPC-Web Route Design

### 1. Multi-Service gRPC-Web Support

**Current limitation:** Only registry-service is configured for gRPC-Web
**Enhancement:** Support multiple services with standardized naming

```yaml
# Enhanced service definitions
services:
  # Registry Service gRPC
  - name: registry-grpc-service
    host: registry-service.service.consul
    port: 50051
    protocol: grpc
    connect_timeout: 5000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    routes:
      - name: registry-grpc-web
        paths:
          - /grpc/v1/registry
        strip_path: true
        protocols:
          - http
          - https
        preserve_host: false
        regex_priority: 100
    tags:
      - grpc
      - registry
      - transcoding

  # Future: Pricing Service gRPC
  - name: pricing-grpc-service
    host: pricing-service.service.consul
    port: 50052
    protocol: grpc
    connect_timeout: 5000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    routes:
      - name: pricing-grpc-web
        paths:
          - /grpc/v1/pricing
        strip_path: true
        protocols:
          - http
          - https
        preserve_host: false
        regex_priority: 100
    tags:
      - grpc
      - pricing
      - transcoding

  # Future: Risk Service gRPC
  - name: risk-grpc-service
    host: risk-service.service.consul
    port: 50053
    protocol: grpc
    connect_timeout: 5000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    routes:
      - name: risk-grpc-web
        paths:
          - /grpc/v1/risk
        strip_path: true
        protocols:
          - http
          - https
        preserve_host: false
        regex_priority: 100
    tags:
      - grpc
      - risk
      - transcoding
```

### 2. Enhanced gRPC-Web Plugin Configuration

**Current limitation:** Basic plugin with minimal configuration
**Enhancement:** Full-featured plugin with proto file support and advanced options

```yaml
plugins:
  # Registry Service gRPC-Web Plugin
  - name: grpc-web
    service: registry-grpc-service
    config:
      proto: /kong/protos/registry.proto
      pass_stripped_path: false
      cors_origin: "*"
      allow_origin_header: true
    tags:
      - grpc-web
      - registry

  # Future: Pricing Service gRPC-Web Plugin
  - name: grpc-web
    service: pricing-grpc-service
    config:
      proto: /kong/protos/pricing.proto
      pass_stripped_path: false
      cors_origin: "*"
      allow_origin_header: true
    tags:
      - grpc-web
      - pricing

  # Future: Risk Service gRPC-Web Plugin
  - name: grpc-web
    service: risk-grpc-service
    config:
      proto: /kong/protos/risk.proto
      pass_stripped_path: false
      cors_origin: "*"
      allow_origin_header: true
    tags:
      - grpc-web
      - risk
```

### 3. Proto File Management

**Directory structure:**
```
gateway/
├── protos/
│   ├── registry.proto      # Registry service proto
│   ├── pricing.proto       # Future: Pricing service proto
│   ├── risk.proto          # Future: Risk service proto
│   └── common/             # Future: Common proto files
│       ├── health.proto    # Health check protos
│       └── errors.proto    # Error handling protos
```

**Docker volume mounting:**
```yaml
# In docker-compose.gateway.yaml
volumes:
  - ./protos:/kong/protos:ro
```

### 4. URL Route Conventions

| Service | gRPC Endpoint | gRPC-Web Route | Content-Type |
|---------|---------------|----------------|--------------|
| Registry | `registry-service:50051` | `/grpc/v1/registry/*` | `application/grpc-web+proto` |
| Pricing | `pricing-service:50052` | `/grpc/v1/pricing/*` | `application/grpc-web+proto` |
| Risk | `risk-service:50053` | `/grpc/v1/risk/*` | `application/grpc-web+proto` |

**Method mapping example:**
```
gRPC Call: venturestrat.registry.v1.RegistryService/Register
gRPC-Web URL: POST /grpc/v1/registry/venturestrat.registry.v1.RegistryService/Register
Content-Type: application/grpc-web+proto
```

### 5. Authentication for gRPC-Web

gRPC-Web routes should use the same authentication as REST routes:

```yaml
# Authentication applies to gRPC-Web routes
# API Key authentication (existing global plugin)
# JWT authentication (existing global plugin)
# Rate limiting (existing global plugin)

# No special authentication overrides needed
# gRPC-Web routes inherit global auth plugins
```

### 6. CORS Configuration for gRPC-Web

Enhanced CORS to support gRPC-Web specific headers:

```yaml
plugins:
  - name: cors
    config:
      origins:
        - "http://localhost:3000"
        - "https://*.venturestrat.io"
      methods:
        - GET
        - POST
        - PUT
        - DELETE
        - PATCH
        - OPTIONS
      headers:
        - Accept
        - Accept-Version
        - Content-Length
        - Content-MD5
        - Content-Type
        - Date
        - Authorization
        - X-API-Key
        - X-Correlation-ID
        - X-Grpc-Web              # gRPC-Web specific
        - Grpc-Timeout            # gRPC-Web specific
        - Grpc-Accept-Encoding    # gRPC-Web specific
      exposed_headers:
        - X-Correlation-ID
        - X-RateLimit-Limit-Minute
        - X-RateLimit-Remaining-Minute
        - X-Kong-Upstream-Latency
        - X-Kong-Proxy-Latency
        - Grpc-Status             # gRPC-Web specific
        - Grpc-Message            # gRPC-Web specific
      credentials: true
      max_age: 3600
      preflight_continue: false
```

## Implementation Strategy

### Phase 1: Registry Service (Current - Task 13.1)
- ✅ Copy registry.proto to gateway/protos/
- ✅ Configure gRPC-Web plugin with proto file
- ✅ Test gRPC-Web transcoding
- ✅ Verify authentication works with gRPC-Web

### Phase 2: Multi-Service Support (Future)
- Add pricing.proto and risk.proto files
- Configure additional gRPC services
- Test service isolation
- Performance testing

### Phase 3: Advanced Features (Future)
- Streaming support
- Custom error handling
- Metrics collection
- Load balancing optimization

## Testing Strategy

### Unit Tests
- Kong configuration validation
- Proto file presence verification
- Plugin configuration validation

### Integration Tests
- gRPC-Web content type handling
- Authentication flow with gRPC-Web
- CORS preflight requests
- Error response transcoding

### End-to-End Tests
- Browser client calling gRPC service
- Full authentication flow
- Rate limiting with gRPC-Web
- Service discovery integration

## Security Considerations

1. **Proto File Security**: Proto files are read-only mounted
2. **CORS Restrictions**: Limited to specific origins in production
3. **Authentication Required**: All gRPC-Web calls require auth (API key or JWT)
4. **Rate Limiting**: Same limits apply to gRPC-Web as REST
5. **Input Validation**: Protobuf validation at service level

## Performance Considerations

1. **Proto Compilation**: Proto files compiled at Kong startup
2. **Transcoding Overhead**: ~10-20ms added latency for transcoding
3. **Connection Pooling**: gRPC connections pooled by Kong
4. **Streaming Support**: Limited by Kong's gRPC-Web plugin capabilities

## Configuration Files Updated

1. `kong.yaml` - Enhanced gRPC-Web service and plugin config
2. `docker-compose.gateway.yaml` - Proto file volume mount
3. `protos/registry.proto` - Registry service protocol definition

## Client Usage Examples

### JavaScript/TypeScript Browser Client

```javascript
// Using grpc-web client
import {RegistryServiceClient} from './generated/registry_grpc_web_pb';
import {RegisterRequest} from './generated/registry_pb';

const client = new RegistryServiceClient('http://localhost:8000/grpc/v1/registry');

const request = new RegisterRequest();
request.setName('test-service');
request.setVersion('1.0.0');

client.register(request, {
  'X-API-Key': 'dev-api-key-12345'
}, (err, response) => {
  if (err) {
    console.error('Registration failed:', err);
  } else {
    console.log('Registered:', response.getInstanceId());
  }
});
```

### cURL Testing

```bash
# Test gRPC-Web endpoint
curl -X POST http://localhost:8000/grpc/v1/registry/venturestrat.registry.v1.RegistryService/Register \
  -H "Content-Type: application/grpc-web+proto" \
  -H "X-API-Key: dev-api-key-12345" \
  -H "X-Grpc-Web: 1" \
  --data-binary @register_request.pb
```

## Success Criteria

- ✅ Registry service accessible via gRPC-Web at `/grpc/v1/registry/*`
- ✅ Authentication works with gRPC-Web requests
- ✅ CORS configured for browser access
- ✅ Proto file correctly loaded and accessible
- ✅ Error handling returns appropriate gRPC status codes
- ✅ Rate limiting applies to gRPC-Web requests
- ✅ Tests verify all functionality

## Future Enhancements

1. **Streaming Support**: Implement server-side streaming for real-time data
2. **Advanced Routing**: Path-based routing for different gRPC methods
3. **Custom Transcoding**: Custom JSON-to-Protobuf transcoding rules
4. **Health Checks**: gRPC health check integration
5. **Load Balancing**: Advanced load balancing for gRPC endpoints
