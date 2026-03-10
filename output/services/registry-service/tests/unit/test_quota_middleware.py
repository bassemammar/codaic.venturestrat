"""Unit tests for QuotaMiddleware.

This test suite tests the QuotaMiddleware implementation including:
1. Redis quota manager functionality
2. 429 response generation
3. Quota enforcement logic
4. Edge cases and error handling

Task 12.3: Implement QuotaMiddleware - Unit Tests
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from registry.middleware.quota import QuotaMiddleware, RedisQuotaManager
from registry.models.tenant_quotas import TenantQuotas
from registry.tenant_service import TenantService
from starlette.applications import Starlette
from starlette.responses import JSONResponse


@pytest.fixture
def mock_redis():
    """Mock Redis client with realistic behavior."""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = 86400
    return redis_mock


@pytest.fixture
def mock_tenant_service():
    """Mock TenantService."""
    service = Mock(spec=TenantService)
    service.get_tenant = AsyncMock()
    return service


@pytest.fixture
def sample_tenant_id():
    """Generate a sample tenant ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_quotas(sample_tenant_id):
    """Create sample quota configuration."""
    return TenantQuotas(
        tenant_id=sample_tenant_id,
        max_users=10,
        max_api_calls_per_day=100,
        max_storage_mb=1024,
        max_records_per_model=10000,
    )


class TestRedisQuotaManager:
    """Test Redis quota manager functionality."""

    def test_redis_key_generation(self, mock_redis, sample_tenant_id):
        """Test Redis key generation for different quota types."""
        manager = RedisQuotaManager(mock_redis)

        # API quota key
        api_key = manager.get_api_quota_key(sample_tenant_id)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        assert api_key == f"quota:api:{sample_tenant_id}:{today}"

        # User quota key
        user_key = manager.get_user_quota_key(sample_tenant_id)
        assert user_key == f"quota:users:{sample_tenant_id}"

        # Storage quota key
        storage_key = manager.get_storage_quota_key(sample_tenant_id)
        assert storage_key == f"quota:storage:{sample_tenant_id}"

    def test_redis_key_generation_with_custom_date(self, mock_redis, sample_tenant_id):
        """Test API quota key generation with custom date."""
        manager = RedisQuotaManager(mock_redis)

        custom_date = "2026-01-15"
        api_key = manager.get_api_quota_key(sample_tenant_id, custom_date)
        assert api_key == f"quota:api:{sample_tenant_id}:{custom_date}"

    async def test_api_counter_increment(self, mock_redis, sample_tenant_id):
        """Test API counter increment functionality."""
        manager = RedisQuotaManager(mock_redis)

        # Mock Redis responses
        mock_redis.incr.return_value = 5
        mock_redis.ttl.return_value = 86400  # Has TTL

        count = await manager.increment_api_counter(sample_tenant_id)

        assert count == 5
        expected_key = manager.get_api_quota_key(sample_tenant_id)
        mock_redis.incr.assert_called_once_with(expected_key)

    async def test_api_counter_sets_expiration_on_first_increment(
        self, mock_redis, sample_tenant_id
    ):
        """Test that API counter sets expiration on first increment."""
        manager = RedisQuotaManager(mock_redis)

        # First increment of the day
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = -1  # No TTL set

        await manager.increment_api_counter(sample_tenant_id)

        # Should call expire
        expected_key = manager.get_api_quota_key(sample_tenant_id)
        mock_redis.expire.assert_called_once()
        expire_call = mock_redis.expire.call_args
        assert expire_call[0][0] == expected_key
        assert expire_call[0][1] > 0  # TTL should be positive
        assert expire_call[0][1] <= 86400  # TTL should be <= 24 hours

    async def test_get_current_api_count(self, mock_redis, sample_tenant_id):
        """Test getting current API count."""
        manager = RedisQuotaManager(mock_redis)

        # Test with existing count
        mock_redis.get.return_value = b"42"
        count = await manager.get_current_api_count(sample_tenant_id)
        assert count == 42

        # Test with no existing count
        mock_redis.get.return_value = None
        count = await manager.get_current_api_count(sample_tenant_id)
        assert count == 0

    async def test_check_and_increment_api_quota_within_limit(
        self, mock_redis, sample_tenant_id, sample_quotas
    ):
        """Test quota check and increment when within limit."""
        manager = RedisQuotaManager(mock_redis)

        # Current count is 50, quota is 100
        mock_redis.get.return_value = b"50"
        mock_redis.incr.return_value = 51

        result = await manager.check_and_increment_api_quota(sample_tenant_id, sample_quotas)

        assert result["allowed"] is True
        assert result["current_count"] == 51
        assert result["limit"] == 100
        assert result["remaining"] == 49
        assert result["usage_percentage"] == 51.0

    async def test_check_and_increment_api_quota_exceeds_limit(
        self, mock_redis, sample_tenant_id, sample_quotas
    ):
        """Test quota check when would exceed limit."""
        manager = RedisQuotaManager(mock_redis)

        # Current count is 100, quota is 100 (at limit)
        mock_redis.get.return_value = b"100"

        result = await manager.check_and_increment_api_quota(sample_tenant_id, sample_quotas)

        assert result["allowed"] is False
        assert result["current_count"] == 100
        assert result["limit"] == 100
        assert result["remaining"] == 0
        assert result["usage_percentage"] == 100.0

        # Should not call incr when quota would be exceeded
        mock_redis.incr.assert_not_called()

    async def test_check_and_increment_api_quota_redis_error(
        self, mock_redis, sample_tenant_id, sample_quotas
    ):
        """Test quota check when Redis fails."""
        manager = RedisQuotaManager(mock_redis)

        # Mock Redis error
        mock_redis.get.side_effect = ConnectionError("Redis connection failed")

        result = await manager.check_and_increment_api_quota(sample_tenant_id, sample_quotas)

        # Should allow request on Redis failure
        assert result["allowed"] is True
        assert result["current_count"] == 0
        assert result["limit"] == 100
        assert result["remaining"] == 100
        assert "redis_error" in result


class TestQuotaMiddleware:
    """Test QuotaMiddleware functionality."""

    def create_test_app(self, middleware):
        """Create test app with middleware."""
        app = Starlette()

        app.add_middleware(middleware.__class__, **middleware.__dict__)

        @app.route("/api/v1/test", methods=["POST"])
        async def test_endpoint(request):
            return JSONResponse({"message": "success"})

        @app.route("/health")
        async def health_endpoint(request):
            return JSONResponse({"status": "ok"})

        return app

    def test_middleware_initialization(self, mock_redis, mock_tenant_service):
        """Test QuotaMiddleware initialization."""
        middleware = QuotaMiddleware(
            app=None,
            redis_client=mock_redis,
            tenant_service=mock_tenant_service,
            exclude_paths=["/custom"],
        )

        assert middleware.redis_client == mock_redis
        assert middleware.tenant_service == mock_tenant_service
        assert "/custom" in middleware.exclude_paths
        assert middleware.quota_manager is not None

    def test_middleware_initialization_without_redis(self, mock_tenant_service):
        """Test QuotaMiddleware initialization without Redis."""
        middleware = QuotaMiddleware(
            app=None, redis_client=None, tenant_service=mock_tenant_service
        )

        assert middleware.redis_client is None
        assert middleware.quota_manager is None

    async def test_exclude_paths_bypassed(self, mock_redis, mock_tenant_service):
        """Test that excluded paths bypass quota middleware."""
        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        # Mock request to excluded path
        request = Mock()
        request.url.path = "/health"
        request.state = Mock()
        call_next = AsyncMock()
        call_next.return_value = JSONResponse({"status": "ok"})

        await middleware.dispatch(request, call_next)

        # Should call next without quota checks
        call_next.assert_called_once()
        # Since path is excluded, quota_info should not be set
        assert not hasattr(request.state, "quota_info")

    async def test_get_methods_bypassed(self, mock_redis, mock_tenant_service, sample_tenant_id):
        """Test that GET/HEAD/OPTIONS methods bypass quota enforcement."""
        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        for method in ["GET", "HEAD", "OPTIONS"]:
            request = Mock()
            request.method = method
            request.url.path = "/api/v1/test"
            request.headers = {"X-Tenant-ID": sample_tenant_id}
            request.state = Mock()
            call_next = AsyncMock()
            call_next.return_value = JSONResponse({"status": "ok"})

            await middleware.dispatch(request, call_next)

            call_next.assert_called()
            # Since method is GET/HEAD/OPTIONS, quota_info should not be set
            assert not hasattr(request.state, "quota_info")

    async def test_missing_tenant_header_bypassed(self, mock_redis, mock_tenant_service):
        """Test that requests without X-Tenant-ID header are bypassed."""
        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {}  # No X-Tenant-ID header
        call_next = AsyncMock()
        call_next.return_value = JSONResponse({"status": "ok"})

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once()

    async def test_quota_enforcement_within_limit(
        self, mock_redis, mock_tenant_service, sample_tenant_id, sample_quotas
    ):
        """Test quota enforcement when request is within limit."""
        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {
            "id": sample_tenant_id,
            "quotas": sample_quotas,
        }
        mock_redis.get.return_value = b"50"
        mock_redis.incr.return_value = 51

        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        # Mock request
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"X-Tenant-ID": sample_tenant_id}
        request.state = Mock()

        call_next = AsyncMock()
        response_mock = Mock()
        response_mock.headers = {}
        call_next.return_value = response_mock

        await middleware.dispatch(request, call_next)

        # Should call next and add quota headers
        call_next.assert_called_once()
        assert hasattr(request.state, "quota_info")
        assert "X-RateLimit-Limit" in response_mock.headers
        assert "X-RateLimit-Remaining" in response_mock.headers

    async def test_quota_enforcement_exceeds_limit(
        self, mock_redis, mock_tenant_service, sample_tenant_id, sample_quotas
    ):
        """Test quota enforcement when request exceeds limit."""
        # Setup mocks - at quota limit (100 for sample_quotas)
        mock_tenant_service.get_tenant.return_value = {
            "id": sample_tenant_id,
            "quotas": sample_quotas,
        }
        mock_redis.get.return_value = b"100"  # At daily limit of 100

        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        # Mock request
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"X-Tenant-ID": sample_tenant_id}
        request.state = Mock()

        call_next = AsyncMock()

        result = await middleware.dispatch(request, call_next)

        # Should return 429 without calling next
        call_next.assert_not_called()
        assert isinstance(result, JSONResponse)
        assert result.status_code == 429

    async def test_middleware_error_handling(
        self, mock_redis, mock_tenant_service, sample_tenant_id
    ):
        """Test middleware error handling."""
        # Setup mock to throw error
        mock_tenant_service.get_tenant.side_effect = Exception("Database error")

        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"X-Tenant-ID": sample_tenant_id}
        request.state = Mock()

        call_next = AsyncMock()
        call_next.return_value = JSONResponse({"status": "ok"})

        await middleware.dispatch(request, call_next)

        # Should call next on error (fail open)
        call_next.assert_called_once()

    def test_429_response_generation(self, mock_redis, mock_tenant_service):
        """Test 429 response generation."""
        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        quota_result = {
            "allowed": False,
            "current_count": 105,
            "limit": 100,
            "remaining": 0,
            "usage_percentage": 105.0,
        }

        request = Mock()
        request.headers = {"X-Tenant-ID": "test-tenant"}
        request.state = Mock()
        request.state.request_id = "test-request-id"

        response = middleware._generate_429_response(
            quota_type="api_calls", quota_result=quota_result, request=request
        )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 429

        # Check headers
        assert "Retry-After" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert response.headers["X-Request-ID"] == "test-request-id"

        # Check body content
        assert response.body is not None

    def test_retry_after_calculation(self, mock_redis, mock_tenant_service):
        """Test retry-after calculation for different quota types."""
        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        quota_result = {"limit": 100, "current_count": 101, "remaining": 0}

        # API calls - should return time until midnight
        api_retry = middleware._calculate_retry_after("api_calls", quota_result)
        assert 0 < api_retry <= 86400

        # Users - should return 1 hour
        user_retry = middleware._calculate_retry_after("users", quota_result)
        assert user_retry == 3600

        # Storage - should return 30 minutes
        storage_retry = middleware._calculate_retry_after("storage", quota_result)
        assert storage_retry == 1800

        # Unknown - should return 5 minutes
        unknown_retry = middleware._calculate_retry_after("unknown", quota_result)
        assert unknown_retry == 300

    def test_reset_timestamp_generation(self, mock_redis, mock_tenant_service):
        """Test quota reset timestamp generation."""
        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        reset_time = middleware._get_reset_timestamp()

        # Should be valid ISO format
        parsed_time = datetime.fromisoformat(reset_time.replace("Z", "+00:00"))
        assert parsed_time > datetime.now(UTC)

        # Should be tomorrow at midnight UTC
        now = datetime.now(UTC)
        expected_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        assert abs((parsed_time - expected_reset).total_seconds()) < 60  # Within 1 minute tolerance


class TestQuotaMiddlewareIntegration:
    """Integration tests for QuotaMiddleware with real request flow."""

    async def test_end_to_end_quota_enforcement(
        self, mock_redis, mock_tenant_service, sample_tenant_id, sample_quotas
    ):
        """Test end-to-end quota enforcement flow."""
        # Setup mocks
        mock_tenant_service.get_tenant.return_value = {
            "id": sample_tenant_id,
            "quotas": sample_quotas,
        }

        # Test sequence: allowed -> allowed -> denied
        mock_redis.get.side_effect = [b"98", b"99", b"100"]
        mock_redis.incr.side_effect = [99, 100]

        middleware = QuotaMiddleware(
            app=Mock(), redis_client=mock_redis, tenant_service=mock_tenant_service
        )

        # First request - should be allowed
        request1 = Mock()
        request1.method = "POST"
        request1.url.path = "/api/v1/test"
        request1.headers = {"X-Tenant-ID": sample_tenant_id}
        request1.state = Mock()

        call_next1 = AsyncMock()
        response1_mock = Mock()
        response1_mock.headers = {}
        call_next1.return_value = response1_mock

        await middleware.dispatch(request1, call_next1)

        # Should be allowed
        call_next1.assert_called_once()
        assert "X-RateLimit-Remaining" in response1_mock.headers

        # Second request - should be allowed (at limit)
        request2 = Mock()
        request2.method = "POST"
        request2.url.path = "/api/v1/test"
        request2.headers = {"X-Tenant-ID": sample_tenant_id}
        request2.state = Mock()

        call_next2 = AsyncMock()
        response2_mock = Mock()
        response2_mock.headers = {}
        call_next2.return_value = response2_mock

        await middleware.dispatch(request2, call_next2)

        # Should be allowed
        call_next2.assert_called_once()

        # Third request - should be denied
        request3 = Mock()
        request3.method = "POST"
        request3.url.path = "/api/v1/test"
        request3.headers = {"X-Tenant-ID": sample_tenant_id}
        request3.state = Mock()

        call_next3 = AsyncMock()

        result3 = await middleware.dispatch(request3, call_next3)

        # Should return 429
        call_next3.assert_not_called()
        assert isinstance(result3, JSONResponse)
        assert result3.status_code == 429
