"""End-to-End Quota Enforcement Tests.

These tests verify the complete quota enforcement flow:
1. Setup tenant with specific quota limits
2. Make requests to exceed the quota
3. Verify 429 responses with proper headers and body
4. Test different quota types (API calls, users, etc.)

This covers the full quota enforcement pipeline from middleware through Redis.
"""
import asyncio
import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from httpx import AsyncClient
from registry.middleware.quota import QuotaMiddleware, RedisQuotaManager
from registry.models.tenant_quotas import TenantQuotas


# Mock tenancy context for testing
class TenantContext:
    def __init__(self, tenant_id: str, tenant_slug: str = None, is_system: bool = False):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.is_system = is_system


def set_current_tenant(context: TenantContext):
    """Mock implementation for testing."""
    pass


# These tests require Redis and integration setup
pytestmark = [
    pytest.mark.integration,
    pytest.mark.containers,
    pytest.mark.quota_enforcement,
    pytest.mark.slow,
]


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    client = redis.Redis.from_url("redis://localhost:6379")
    await client.flushall()  # Clean slate for each test
    yield client
    await client.flushall()  # Cleanup
    await client.close()


@pytest.fixture
def sample_tenant_id():
    """Generate a sample tenant ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
async def quota_manager(redis_client):
    """Create RedisQuotaManager for testing."""
    return RedisQuotaManager(redis_client)


@pytest.fixture
def low_quota_config():
    """Create a low quota configuration for easy testing."""
    return {
        "max_api_calls_per_day": 5,
        "max_users": 3,
        "max_storage_mb": 10,
        "max_records_per_model": 50,
    }


@pytest.fixture
def mock_tenant_service():
    """Mock TenantService for quota enforcement."""
    service = AsyncMock()

    async def get_tenant_quotas_mock(tenant_id: str) -> TenantQuotas:
        # Return low quotas for testing
        return TenantQuotas(
            tenant_id=tenant_id,
            max_api_calls_per_day=5,
            max_users=3,
            max_storage_mb=10,
            max_records_per_model=50,
        )

    service.get_tenant_quotas = get_tenant_quotas_mock
    return service


@pytest.fixture
def test_app(mock_tenant_service, redis_client):
    """Create FastAPI test app with QuotaMiddleware."""
    app = FastAPI()

    # Add quota middleware
    app.add_middleware(
        QuotaMiddleware, tenant_service=mock_tenant_service, redis_client=redis_client
    )

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "success"}

    @app.post("/api/v1/test")
    async def test_post_endpoint():
        return {"message": "created"}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}

    return app


class TestAPIQuotaE2E:
    """End-to-end tests for API call quota enforcement."""

    @pytest.mark.asyncio
    async def test_e2e_api_quota_exceed_returns_429(self, test_app, sample_tenant_id, redis_client):
        """Test complete E2E flow: exceed API quota and verify 429 response."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Set tenant context
            set_current_tenant(TenantContext(tenant_id=sample_tenant_id))

            # Make requests up to the limit (5 API calls per day)
            success_responses = []
            for i in range(5):
                response = await client.post(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )
                success_responses.append(response)

                # All should succeed initially
                assert response.status_code == 200, f"Request {i+1} should succeed"
                assert response.json() == {"message": "created"}

            # The 6th request should trigger 429
            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

            # Verify 429 response
            assert response.status_code == 429, "6th request should return 429"

            # Verify 429 response headers
            assert "Retry-After" in response.headers, "429 should include Retry-After header"
            assert "X-RateLimit-Limit" in response.headers, "429 should include rate limit"
            assert "X-RateLimit-Remaining" in response.headers, "429 should include remaining count"

            # Verify header values
            assert response.headers["X-RateLimit-Limit"] == "5", "Rate limit should match quota"
            assert response.headers["X-RateLimit-Remaining"] == "0", "Remaining should be 0"

            retry_after = int(response.headers["Retry-After"])
            assert 0 < retry_after <= 86400, "Retry-After should be reasonable (0 < x <= 24hrs)"

            # Verify 429 response body
            body = response.json()
            assert body["error"] == "quota_exceeded", "Error type should be quota_exceeded"
            assert body["quota_type"] == "api_calls", "Should specify API calls quota"
            assert body["current_usage"] == 6, "Should show current usage"
            assert body["limit"] == 5, "Should show the limit"
            assert body["remaining"] == 0, "Should show 0 remaining"
            assert body["retry_after_seconds"] == retry_after, "Body retry should match header"
            assert "API call quota exceeded" in body["message"], "Message should be descriptive"

    @pytest.mark.asyncio
    async def test_e2e_quota_redis_counter_persistence(
        self, test_app, sample_tenant_id, redis_client
    ):
        """Test that quota counters persist correctly in Redis."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Make 3 API calls
            for i in range(3):
                response = await client.post(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )
                assert response.status_code == 200

            # Check Redis counter directly
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            key = f"api_quota:{sample_tenant_id}:{today}"
            count = await redis_client.get(key)

            assert count is not None, "Redis counter should exist"
            assert int(count) == 3, "Redis counter should show 3 calls"

            # Verify TTL is set (should expire within 24 hours)
            ttl = await redis_client.ttl(key)
            assert ttl > 0, "Redis key should have TTL set"
            assert ttl <= 86400, "TTL should be within 24 hours"

    @pytest.mark.asyncio
    async def test_e2e_quota_different_tenants_isolated(self, test_app, redis_client):
        """Test that quota counters are isolated between different tenants."""
        tenant_a_id = str(uuid.uuid4())
        tenant_b_id = str(uuid.uuid4())

        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Tenant A makes 4 calls (within limit)
            for _ in range(4):
                response = await client.post("/api/v1/test", headers={"X-Tenant-ID": tenant_a_id})
                assert response.status_code == 200

            # Tenant B makes 4 calls (also within limit)
            for _ in range(4):
                response = await client.post("/api/v1/test", headers={"X-Tenant-ID": tenant_b_id})
                assert response.status_code == 200

            # Both tenants can make 1 more call (their 5th, at the limit)
            response_a = await client.post("/api/v1/test", headers={"X-Tenant-ID": tenant_a_id})
            assert response_a.status_code == 200, "Tenant A should reach their limit"

            response_b = await client.post("/api/v1/test", headers={"X-Tenant-ID": tenant_b_id})
            assert response_b.status_code == 200, "Tenant B should reach their limit"

            # Next calls for both should fail with 429
            response_a_over = await client.post(
                "/api/v1/test", headers={"X-Tenant-ID": tenant_a_id}
            )
            assert response_a_over.status_code == 429, "Tenant A should get 429"

            response_b_over = await client.post(
                "/api/v1/test", headers={"X-Tenant-ID": tenant_b_id}
            )
            assert response_b_over.status_code == 429, "Tenant B should get 429"

    @pytest.mark.asyncio
    async def test_e2e_quota_read_operations_excluded(self, test_app, sample_tenant_id):
        """Test that read operations (GET) are excluded from API quota."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Make 10 GET requests (should not count against quota)
            for _ in range(10):
                response = await client.get(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )
                assert response.status_code == 200

            # Now make 5 POST requests (these count against quota)
            for _ in range(5):
                response = await client.post(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )
                assert response.status_code == 200

            # The 6th POST should trigger 429
            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
            assert response.status_code == 429

            # But GET requests should still work
            response = await client.get("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
            assert (
                response.status_code == 200
            ), "GET requests should still work after quota exceeded"

    @pytest.mark.asyncio
    async def test_e2e_quota_health_endpoint_excluded(self, test_app, sample_tenant_id):
        """Test that health endpoints are excluded from quota enforcement."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Exhaust the quota with POST requests
            for _ in range(5):
                response = await client.post(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )
                assert response.status_code == 200

            # Verify quota is exceeded
            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
            assert response.status_code == 429

            # Health endpoint should still work without X-Tenant-ID header
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}


class TestQuotaMiddlewareIntegration:
    """Integration tests for the complete quota middleware pipeline."""

    @pytest.mark.asyncio
    async def test_e2e_quota_middleware_redis_integration(self, redis_client, sample_tenant_id):
        """Test QuotaMiddleware integrates correctly with Redis."""
        # Create quota manager
        quota_manager = RedisQuotaManager(redis_client)

        # Create test quotas
        quotas = TenantQuotas(
            tenant_id=sample_tenant_id,
            max_api_calls_per_day=3,
            max_users=5,
            max_storage_mb=100,
            max_records_per_model=1000,
        )

        # Test quota checking with increment
        result1 = await quota_manager.check_and_increment_api_quota(sample_tenant_id, quotas)
        assert result1["allowed"] is True
        assert result1["current_count"] == 1
        assert result1["remaining"] == 2

        result2 = await quota_manager.check_and_increment_api_quota(sample_tenant_id, quotas)
        assert result2["allowed"] is True
        assert result2["current_count"] == 2
        assert result2["remaining"] == 1

        result3 = await quota_manager.check_and_increment_api_quota(sample_tenant_id, quotas)
        assert result3["allowed"] is True
        assert result3["current_count"] == 3
        assert result3["remaining"] == 0

        # 4th call should exceed quota
        result4 = await quota_manager.check_and_increment_api_quota(sample_tenant_id, quotas)
        assert result4["allowed"] is False
        assert result4["current_count"] == 4
        assert result4["remaining"] == 0
        assert result4["usage_percentage"] > 100

    @pytest.mark.asyncio
    async def test_e2e_quota_exception_to_429_conversion(self, test_app, sample_tenant_id):
        """Test that QuotaExceededException is properly converted to 429 response."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Exhaust quota with 5 requests
            for _ in range(5):
                await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

            # Next request should raise QuotaExceededException and return 429
            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

            assert response.status_code == 429
            body = response.json()

            # Verify it contains all expected fields from QuotaExceededException
            expected_fields = [
                "error",
                "message",
                "quota_type",
                "current_usage",
                "limit",
                "remaining",
                "usage_percentage",
                "retry_after_seconds",
            ]

            for field in expected_fields:
                assert field in body, f"429 response should contain {field}"

    @pytest.mark.asyncio
    async def test_e2e_concurrent_requests_quota_enforcement(self, test_app, sample_tenant_id):
        """Test quota enforcement under concurrent request load."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Create 10 concurrent requests (quota limit is 5)
            async def make_request(request_num):
                return await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

            # Execute requests concurrently
            tasks = [make_request(i) for i in range(10)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter successful vs failed responses
            success_responses = [
                r for r in responses if hasattr(r, "status_code") and r.status_code == 200
            ]
            quota_exceeded_responses = [
                r for r in responses if hasattr(r, "status_code") and r.status_code == 429
            ]

            # Should have some successful and some failed responses
            assert len(success_responses) <= 5, "Should not exceed quota limit of 5"
            assert len(quota_exceeded_responses) >= 5, "Should have quota exceeded responses"

            # All 429 responses should have proper structure
            for response in quota_exceeded_responses:
                assert "X-RateLimit-Limit" in response.headers
                body = response.json()
                assert body["error"] == "quota_exceeded"
                assert body["quota_type"] == "api_calls"


class TestQuotaE2EErrorCases:
    """Test error cases and edge conditions in quota enforcement."""

    @pytest.mark.asyncio
    async def test_e2e_quota_redis_failure_graceful_degradation(self, test_app, sample_tenant_id):
        """Test that quota enforcement degrades gracefully when Redis fails."""
        # This test would need a way to simulate Redis failure
        # For now, we test the fail-open behavior by mocking Redis errors

        with patch(
            "registry.middleware.quota.RedisQuotaManager.check_and_increment_api_quota"
        ) as mock_check:
            # Simulate Redis connection error
            mock_check.side_effect = ConnectionError("Redis connection failed")

            async with AsyncClient(app=test_app, base_url="http://test") as client:
                # Requests should still succeed when Redis fails (fail-open)
                response = await client.post(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )

                # Should allow request through (fail-open policy)
                assert response.status_code == 200, "Should fail open when Redis unavailable"

    @pytest.mark.asyncio
    async def test_e2e_quota_invalid_tenant_id(self, test_app):
        """Test quota enforcement with invalid tenant ID."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Request with invalid tenant ID format
            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": "invalid-uuid"})

            # Should get 400 for invalid tenant ID format
            assert response.status_code == 400
            body = response.json()
            assert (
                "invalid_tenant" in body.get("error", "").lower()
                or "tenant" in body.get("message", "").lower()
            )

    @pytest.mark.asyncio
    async def test_e2e_quota_missing_tenant_header(self, test_app):
        """Test quota enforcement when X-Tenant-ID header is missing."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Request without tenant header
            response = await client.post("/api/v1/test")

            # Should get 400 for missing tenant header
            assert response.status_code == 400
            body = response.json()
            assert (
                "missing_tenant" in body.get("error", "").lower()
                or "required" in body.get("message", "").lower()
            )


class TestQuotaPerformanceE2E:
    """Performance tests for quota enforcement."""

    @pytest.mark.asyncio
    async def test_e2e_quota_enforcement_performance(self, test_app, sample_tenant_id):
        """Test that quota enforcement doesn't significantly impact response time."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Measure baseline response time without quota pressure
            start_time = time.time()

            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})

            baseline_time = time.time() - start_time
            assert response.status_code == 200

            # Make requests up to quota limit
            times = []
            for _ in range(4):  # 4 more requests (total 5, at limit)
                start_time = time.time()
                response = await client.post(
                    "/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id}
                )
                request_time = time.time() - start_time
                times.append(request_time)
                assert response.status_code == 200

            # Measure 429 response time
            start_time = time.time()
            response = await client.post("/api/v1/test", headers={"X-Tenant-ID": sample_tenant_id})
            quota_exceeded_time = time.time() - start_time

            assert response.status_code == 429

            # Performance assertions
            avg_time = sum(times) / len(times)

            # Quota checking shouldn't add more than 100ms overhead
            assert (
                avg_time - baseline_time < 0.1
            ), f"Quota checking overhead too high: {avg_time - baseline_time:.3f}s"

            # 429 response should be fast (no need for expensive operations)
            assert quota_exceeded_time < 0.1, f"429 response too slow: {quota_exceeded_time:.3f}s"


# Utility functions for test setup
async def setup_test_data(redis_client, tenant_id: str, initial_count: int = 0):
    """Setup initial quota counter in Redis for testing."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"api_quota:{tenant_id}:{today}"

    if initial_count > 0:
        await redis_client.set(key, initial_count)
        await redis_client.expire(key, 86400)  # 24 hours


async def cleanup_test_data(redis_client, tenant_id: str):
    """Cleanup test data from Redis."""
    pattern = f"*{tenant_id}*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
