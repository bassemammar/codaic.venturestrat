# Rate Limiting Tiers Design

> Task 9.1: Design rate limiting tiers
> Created: 2026-01-05
> Spec: @.agent-os/specs/2026-01-04-api-gateway/

## Overview

This document describes the comprehensive rate limiting tier structure implemented in Kong Gateway for VentureStrat. The design provides differentiated service levels for external API consumers while ensuring platform stability and fair resource allocation.

## Rate Limiting Architecture

### Backend Strategy
- **Policy**: Redis-backed rate limiting for distributed consistency
- **Fault Tolerance**: Enabled (`fault_tolerant: true`) - requests proceed if Redis unavailable
- **Granularity**: Per-consumer limits with global defaults
- **Time Windows**: Minute, Hour, Day buckets for flexible limit enforcement

### Redis Configuration
```yaml
policy: redis
redis_host: redis
redis_port: 6379
redis_timeout: 2000
fault_tolerant: true
hide_client_headers: false
```

## Consumer Tiers

### 1. Global Default Tier
**Consumer**: All authenticated consumers (fallback)
**Use Case**: Default limits for any API key consumer not explicitly configured

```yaml
Rate Limits:
- Minute: 1000 requests
- Hour: 10000 requests
```

**Headers Exposed**:
- `X-RateLimit-Limit-Minute`
- `X-RateLimit-Remaining-Minute`

### 2. Free Tier
**Consumer**: `free-tier-consumer`
**API Key**: `free-api-key-11111`
**Use Case**: Trial users, basic integrations, development/testing

```yaml
Rate Limits:
- Minute: 100 requests (10x less than global)
- Hour: 1000 requests
- Day: 2500 requests
```

**Target Personas**:
- Developers evaluating the platform
- Small-scale integrations
- Proof-of-concept implementations

### 3. Standard Tier
**Consumer**: `standard-tier-consumer`
**API Key**: `standard-api-key-22222`
**Use Case**: Production workloads, regular business operations

```yaml
Rate Limits:
- Minute: 1000 requests (same as global)
- Hour: 10000 requests
- Day: 50000 requests
```

**Target Personas**:
- Mid-market treasury departments
- Regular production trading systems
- Standard SaaS customers

### 4. Premium Tier
**Consumer**: `premium-tier-consumer`
**API Key**: `premium-api-key-33333`
**Use Case**: High-volume trading, enterprise customers, mission-critical systems

```yaml
Rate Limits:
- Minute: 5000 requests (5x standard)
- Hour: 100000 requests (10x standard)
- Day: 500000 requests (10x standard)
```

**Target Personas**:
- Large investment banks
- High-frequency trading systems
- Enterprise treasury platforms
- Priority/white-glove customers

### 5. Development Tier
**Consumer**: `default-consumer`, `test-consumer`
**API Keys**: `dev-api-key-12345`, `test-api-key-67890`
**Use Case**: Internal development, testing, CI/CD pipelines

```yaml
Rate Limits: Global defaults (1000/min, 10000/hour)
```

## Service-to-Service Tier

### JWT-Authenticated Services
**Authentication**: JWT tokens (not API keys)
**Rate Limiting**: Global defaults or no specific limits
**Use Case**: Internal microservice communication

**Services**:
- `registry-service`
- `pricing-service`
- `jwt-issuer-service`

**Rationale**: Service-to-service calls are trusted and should not be heavily rate-limited. Focus is on external API protection.

## Rate Limit Enforcement

### Response Headers

All responses include rate limiting information:

```http
X-RateLimit-Limit-Minute: 1000
X-RateLimit-Remaining-Minute: 999
X-Kong-Upstream-Latency: 42
X-Kong-Proxy-Latency: 3
```

### Rate Limit Exceeded (429)

When limits are exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 0

{
  "message": "API rate limit exceeded",
  "error": "Too Many Requests"
}
```

### Error Scenarios

1. **Redis Unavailable**: Requests proceed (fault tolerant)
2. **Invalid Consumer**: Falls back to global limits
3. **Concurrent Requests**: Redis atomic operations ensure accuracy

## Configuration Hierarchy

### Priority Order
1. **Consumer-specific limits** (highest priority)
2. **Global plugin limits** (fallback)
3. **No limits** (if rate limiting disabled)

### Example Resolution
```yaml
# Consumer premium-tier-consumer makes request
# 1. Check consumer plugins: 5000/min ✓
# 2. Apply consumer limit: 5000/min
# 3. Global limit ignored: 1000/min
```

## Implementation Details

### Kong Configuration Structure

```yaml
# Global rate limiting plugin
plugins:
  - name: rate-limiting
    config:
      minute: 1000
      hour: 10000
      policy: redis
      redis_host: redis
      redis_port: 6379
      fault_tolerant: true

# Consumer-specific rate limiting
consumers:
  - username: free-tier-consumer
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000
          day: 2500
          policy: redis
          redis_host: redis
          redis_port: 6379
          fault_tolerant: true
```

### Redis Key Structure

Kong uses Redis keys in format:
```
ratelimit:{consumer_id}:{period}:{current_window}
```

Examples:
```
ratelimit:free-tier:60:1704365460
ratelimit:standard-tier:3600:1704364800
```

### Time Window Calculation

- **Minute**: Rolling 60-second window
- **Hour**: Rolling 3600-second window
- **Day**: Rolling 86400-second window

Windows are aligned to Redis server time for consistency across Kong instances.

## Testing Strategy

### Unit Tests
- Kong configuration validation
- Rate limit tier configuration parsing
- Consumer plugin validation

### Integration Tests
- Rate limit header presence
- Tier enforcement (free < standard < premium)
- Redis backend consistency
- Fault tolerance (Redis down)
- Cross-endpoint rate limiting
- Concurrent request handling

### Load Testing
- High-volume tier performance
- Redis scaling under load
- Gateway performance with rate limiting enabled

## Monitoring and Observability

### Prometheus Metrics

Kong exports rate limiting metrics:
```
kong_rate_limit_counter_total{consumer="free-tier-consumer",policy="redis"}
kong_rate_limit_remaining{consumer="standard-tier-consumer"}
```

### Alerting

Key alerts for rate limiting:
1. **High rate limit usage**: Consumer approaching limits
2. **Rate limit violations**: Frequent 429 responses
3. **Redis connectivity**: Rate limiting backend health
4. **Tier migration**: Consumer exceeding current tier

### Logging

Rate limit events are logged with correlation IDs:
```json
{
  "level": "info",
  "message": "rate limit applied",
  "consumer": "free-tier-consumer",
  "limit": 100,
  "remaining": 23,
  "correlation_id": "abc-123-def",
  "timestamp": "2026-01-05T10:30:00Z"
}
```

## Future Enhancements

### Dynamic Rate Limiting
- Real-time tier upgrades/downgrades
- Usage-based automatic tier promotion
- Burst capacity allocation

### Advanced Policies
- Geographic rate limiting
- Endpoint-specific limits
- Time-of-day variations
- Customer-specific SLAs

### Integration
- API key management UI
- Self-service tier upgrades
- Usage analytics dashboard
- Billing integration

## Security Considerations

### DDoS Protection
- Rate limiting is first line of defense
- Coordinates with upstream DDoS protection
- Progressive degradation under attack

### Abuse Prevention
- Multi-tier limits prevent tier circumvention
- Redis backend prevents distributed bypass
- Correlation ID tracking for forensics

### Fair Usage
- Separate consumer quotas prevent resource monopolization
- Burst tolerance for legitimate traffic spikes
- Clear tier boundaries and upgrade paths

## Compliance

### SLA Guarantees
- Free tier: Best effort, no SLA
- Standard tier: 99.5% availability within limits
- Premium tier: 99.9% availability within limits

### Audit Trail
- All rate limit decisions logged
- Consumer usage tracking
- Tier change history
- Performance impact monitoring

This rate limiting tier design ensures fair resource allocation, platform stability, and clear monetization paths while providing excellent developer experience across all customer segments.
