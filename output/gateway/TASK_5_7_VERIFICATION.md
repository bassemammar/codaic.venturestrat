# Task 5.7 Verification: API Key Authentication with curl

## Task: Verify: `curl -H "X-API-Key: dev-api-key-12345" ...`

This verification demonstrates that API key authentication is working correctly using curl commands.

## Setup

Start the gateway and infrastructure:

```bash
# Start infrastructure (Redis, Consul)
docker compose -f docker-compose.infra.yaml up -d

# Start the gateway
docker compose -f gateway/docker-compose.gateway.yaml up -d

# Wait for services to be healthy
sleep 10
```

## Manual Verification Commands

### 1. Test without API key (should return 401)

```bash
curl -v http://localhost:8000/api/v1/registry/services
```

Expected response:
- Status: 401 Unauthorized
- Body contains message about missing API key

### 2. Test with invalid API key (should return 403)

```bash
curl -H "X-API-Key: invalid-key-12345" \
  http://localhost:8000/api/v1/registry/services
```

Expected response:
- Status: 403 Forbidden
- Body contains message about invalid credentials

### 3. Test with valid API key (should pass authentication)

```bash
curl -H "X-API-Key: dev-api-key-12345" \
  http://localhost:8000/api/v1/registry/services
```

Expected response:
- Status: 200 (if registry service is up), 404, 502, or 503 (if service is down)
- NOT 401 or 403 (authentication should pass)
- Response headers include:
  - X-Correlation-ID
  - X-Kong-Proxy-Latency
  - X-RateLimit-Limit-Minute
  - X-RateLimit-Remaining-Minute

### 4. Test with all configured API keys

```bash
# Default consumer
curl -H "X-API-Key: dev-api-key-12345" \
  http://localhost:8000/api/v1/registry/services

# Test consumer
curl -H "X-API-Key: test-api-key-67890" \
  http://localhost:8000/api/v1/registry/services

# Free tier consumer
curl -H "X-API-Key: free-api-key-11111" \
  http://localhost:8000/api/v1/registry/services

# Standard tier consumer
curl -H "X-API-Key: standard-api-key-22222" \
  http://localhost:8000/api/v1/registry/services
```

### 5. Test API key via query parameter

```bash
curl http://localhost:8000/api/v1/registry/services?apikey=dev-api-key-12345
```

### 6. Test health endpoint (should work without API key)

```bash
curl http://localhost:8000/health
```

Expected response:
- Status: 200 or 503 depending on health service availability
- Should NOT require API key

## Automated Verification

Run the automated verification script:

```bash
python gateway/tests/manual/verify_test_consumers.py
```

This script tests all configured consumers and validates authentication behavior.

## Integration Test Verification

Run the integration tests:

```bash
pytest gateway/tests/integration/test_api_key_auth.py -v
```

## Expected Results

✅ **PASS Criteria:**
- Request without API key returns 401
- Request with invalid API key returns 403
- Request with valid API key passes authentication (status NOT 401/403)
- Kong headers are present in successful responses
- All configured API keys work correctly
- Health endpoint works without authentication

❌ **FAIL Criteria:**
- Valid API key returns 401 or 403
- Invalid/missing API key returns 200
- Kong headers missing from responses
- Gateway not responding or throwing errors

## Success Indicators

When verification passes, you should see:
1. **Authentication working**: Valid keys allow requests through
2. **Security enforced**: Invalid/missing keys are rejected
3. **Kong headers**: Response includes Kong-added headers
4. **Consumer isolation**: Different API keys work independently
5. **Rate limiting**: Headers show rate limit information

## Troubleshooting

If verification fails:
1. Check gateway logs: `docker logs kong-gateway`
2. Verify Kong is running: `docker ps | grep kong`
3. Check kong.yaml syntax: `kong config validate gateway/kong.yaml`
4. Verify infrastructure: Redis and Consul should be healthy
5. Test gateway admin API: `curl http://localhost:8001/`

## Completion

Task 5.7 is complete when:
- [x] Manual curl commands with API keys work as expected
- [x] Automated verification script passes
- [x] Integration tests pass
- [x] All configured API keys authenticate successfully
