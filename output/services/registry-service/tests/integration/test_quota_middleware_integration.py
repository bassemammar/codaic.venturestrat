"""Integration tests for QuotaMiddleware with FastAPI.

This test suite tests the full integration of QuotaMiddleware with FastAPI
including real HTTP requests, Redis simulation, and end-to-end quota enforcement.

Task 12.3: Implement QuotaMiddleware - Integration Tests
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request
from registry.middleware.quota import QuotaMiddleware
from registry.tenant_service import TenantService
from starlette.testclient import TestClient


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = 86400
    return redis_mock


@pytest.fixture
def mock_tenant_service():
    """Mock TenantService for testing."""
    service = Mock(spec=TenantService)
    service.get_tenant = AsyncMock()
    return service


@pytest.fixture
def sample_tenant_id():
    """Generate a sample tenant ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_app(mock_redis, mock_tenant_service):
    """Create test FastAPI app with QuotaMiddleware."""
    app = FastAPI(title="Test App")

    # Add quota middleware
    app.add_middleware(
        QuotaMiddleware,
        redis_client=mock_redis,
        tenant_service=mock_tenant_service,
        exclude_paths=["/health", "/docs"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/v1/test")
    async def test_endpoint(request: Request):
        return {"message": "success", "tenant": request.headers.get("X-Tenant-ID")}

    @app.get("/api/v1/read-only")
    async def read_only_endpoint():
        return {"data": "some data"}

    @app.put("/api/v1/update")
    async def update_endpoint():
        return {"message": "updated"}

    return app


class TestQuotaMiddlewareIntegration:
    """Integration tests for QuotaMiddleware with FastAPI."""

    def test_health_endpoint_bypassed(self, test_app, mock_redis, sample_tenant_id):
        """Test that health endpoint bypasses quota middleware."""
        client = TestClient(test_app)

        # Health endpoint should work without X-Tenant-ID
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Redis should not be called
        mock_redis.get.assert_not_called()
        mock_redis.incr.assert_not_called()

    def test_get_request_bypassed(self, test_app, mock_redis, sample_tenant_id):
        """Test that GET requests bypass quota enforcement."""
        client = TestClient(test_app)

        response = client.get("/api/v1/read-only", headers={"X-Tenant-ID": sample_tenant_id})

        assert response.status_code == 200
        assert response.json() == {"data": "some data"}

        # Redis should not be called for GET requests
        mock_redis.get.assert_not_called()
        mock_redis.incr.assert_not_called()

    def test_post_request_without_tenant_header_bypassed(self, test_app, mock_redis):
        """Test that POST without X-Tenant-ID header is bypassed."""
        client = TestClient(test_app)

        response = client.post("/api/v1/test")

        assert response.status_code == 200
        # Quota middleware should let it pass (TenantMiddleware would handle missing header)

    def test_post_request_within_quota_allowed(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test that POST request within quota is allowed."""
        client = TestClient(test_app)

        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}
        mock_redis.get.return_value = b"50"  # Current count
        mock_redis.incr.return_value = 51  # After increment

        response = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

        assert response.status_code == 200
        assert response.json() == {"message": "success", "tenant": sample_tenant_id}

        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Verify Redis calls
        expected_key = f"quota:api:{sample_tenant_id}:{datetime.now(UTC).strftime('%Y-%m-%d')}"
        mock_redis.get.assert_called_with(expected_key)
        mock_redis.incr.assert_called_with(expected_key)

    def test_post_request_exceeds_quota_denied(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test that POST request exceeding quota is denied with 429."""
        client = TestClient(test_app)

        # Setup mocks - at quota limit (default is 100)
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}
        mock_redis.get.return_value = b"100"  # At daily limit

        response = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

        assert response.status_code == 429

        # Verify 429 response structure
        response_data = response.json()
        assert response_data["error"] == "quota_exceeded"
        assert response_data["quota_type"] == "api_calls"
        assert response_data["current_usage"] == 100
        assert response_data["limit"] == 100  # Default quota
        assert response_data["remaining"] == 0

        # Should have standard 429 headers
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

        # Should NOT increment counter when quota exceeded
        mock_redis.incr.assert_not_called()

    def test_put_request_quota_enforcement(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test that PUT request is subject to quota enforcement."""
        client = TestClient(test_app)

        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}
        mock_redis.get.return_value = b"25"
        mock_redis.incr.return_value = 26

        response = client.put("/api/v1/update", headers={"X-Tenant-ID": sample_tenant_id})

        assert response.status_code == 200
        assert response.json() == {"message": "updated"}

        # Should enforce quotas on PUT
        mock_redis.get.assert_called()
        mock_redis.incr.assert_called()

    def test_multiple_requests_quota_progression(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test quota progression through multiple requests."""
        client = TestClient(test_app)

        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}

        # Simulate quota progression: 98 -> 99 -> 100 -> 101 (denied)
        mock_redis.get.side_effect = [b"98", b"99", b"100"]
        mock_redis.incr.side_effect = [99, 100]

        # First request - should succeed
        response1 = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
        assert response1.status_code == 200
        assert response1.headers["X-RateLimit-Remaining"] == "1"

        # Second request - should succeed (at limit)
        response2 = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
        assert response2.status_code == 200
        assert response2.headers["X-RateLimit-Remaining"] == "0"

        # Third request - should fail
        response3 = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
        assert response3.status_code == 429
        assert response3.json()["current_usage"] == 100

    def test_different_tenants_isolated_quotas(self, test_app, mock_redis, mock_tenant_service):
        """Test that different tenants have isolated quota counters."""
        client = TestClient(test_app)

        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {"id": "dummy"}

        # Setup different Redis responses for different tenants
        def redis_get_side_effect(key):
            if tenant1_id in key:
                return b"50"  # Tenant 1 has used 50
            elif tenant2_id in key:
                return b"75"  # Tenant 2 has used 75
            return None

        def redis_incr_side_effect(key):
            if tenant1_id in key:
                return 51
            elif tenant2_id in key:
                return 76
            return 1

        mock_redis.get.side_effect = redis_get_side_effect
        mock_redis.incr.side_effect = redis_incr_side_effect

        # Request from tenant 1
        response1 = client.post("/api/v1/test", headers={"X-Tenant-ID": tenant1_id})
        assert response1.status_code == 200
        assert response1.headers["X-RateLimit-Remaining"] == "49"

        # Request from tenant 2
        response2 = client.post("/api/v1/test", headers={"X-Tenant-ID": tenant2_id})
        assert response2.status_code == 200
        assert response2.headers["X-RateLimit-Remaining"] == "24"

    def test_redis_error_handling_fail_open(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test that Redis errors result in fail-open behavior."""
        client = TestClient(test_app)

        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}
        mock_redis.get.side_effect = ConnectionError("Redis connection failed")

        response = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

        # Should allow request on Redis failure (fail open)
        assert response.status_code == 200
        assert response.json() == {"message": "success", "tenant": sample_tenant_id}

    def test_tenant_service_error_handling(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test error handling when tenant service fails."""
        client = TestClient(test_app)

        # Setup mock to fail
        mock_tenant_service.get_tenant.side_effect = Exception("Database error")

        response = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

        # Should allow request on tenant service failure (fail open)
        assert response.status_code == 200

    def test_429_response_structure_compliance(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test that 429 response structure complies with standards."""
        client = TestClient(test_app)

        # Setup mocks for quota exceeded
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}
        mock_redis.get.return_value = b"100"

        response = client.post(
            "/api/v1/test",
            headers={"X-Tenant-ID": sample_tenant_id, "X-Request-ID": "test-request-123"},
        )

        assert response.status_code == 429

        # Verify standard HTTP headers
        assert "Retry-After" in response.headers
        assert "Content-Type" in response.headers
        assert response.headers["Content-Type"] == "application/json"
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Verify request ID propagation
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == "test-request-123"

        # Verify response body
        data = response.json()
        required_fields = [
            "error",
            "message",
            "quota_type",
            "current_usage",
            "limit",
            "remaining",
            "usage_percentage",
            "retry_after_seconds",
            "reset_time",
        ]
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        assert data["error"] == "quota_exceeded"
        assert data["quota_type"] == "api_calls"
        assert isinstance(data["retry_after_seconds"], int)
        assert data["retry_after_seconds"] > 0

    def test_quota_headers_on_successful_requests(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test that quota information is included in headers on successful requests."""
        client = TestClient(test_app)

        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}
        mock_redis.get.return_value = b"42"
        mock_redis.incr.return_value = 43

        response = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

        assert response.status_code == 200

        # Verify rate limit headers are present and correct
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        assert response.headers["X-RateLimit-Limit"] == "100"  # Default quota
        assert response.headers["X-RateLimit-Remaining"] == "57"  # 100 - 43

        # Reset time should be a valid ISO timestamp
        reset_time = response.headers["X-RateLimit-Reset"]
        parsed_time = datetime.fromisoformat(reset_time.replace("Z", "+00:00"))
        assert parsed_time > datetime.now(UTC)


class TestQuotaMiddlewarePerformance:
    """Performance tests for QuotaMiddleware."""

    def test_middleware_performance_under_load(
        self, test_app, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test middleware performance with multiple rapid requests."""
        client = TestClient(test_app)

        # Setup mocks for high-volume testing
        mock_tenant_service.get_tenant.return_value = {"id": sample_tenant_id}

        # Mock progressive counter
        counter = [0]

        def redis_get_effect(key):
            return str(counter[0]).encode()

        def redis_incr_effect(key):
            counter[0] += 1
            return counter[0]

        mock_redis.get.side_effect = redis_get_effect
        mock_redis.incr.side_effect = redis_incr_effect

        # Make multiple requests rapidly
        responses = []
        for i in range(50):  # Well within quota
            response = client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Headers should be consistent
        for response in responses:
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers

    def test_middleware_memory_efficiency(self, test_app, mock_redis, mock_tenant_service):
        """Test that middleware doesn't accumulate state across requests."""
        client = TestClient(test_app)

        tenants = [str(uuid.uuid4()) for _ in range(10)]
        mock_tenant_service.get_tenant.return_value = {"id": "dummy"}

        # Process requests for multiple tenants
        for tenant_id in tenants:
            mock_redis.get.return_value = b"10"
            mock_redis.incr.return_value = 11

            response = client.post("/api/v1/test", headers={"X-Tenant-ID": tenant_id})
            assert response.status_code == 200

        # Middleware should not accumulate state
        # (This is more of a structural test - real memory testing would require profiling)
