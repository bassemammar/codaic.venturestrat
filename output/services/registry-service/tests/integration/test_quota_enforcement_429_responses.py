"""
Integration tests for quota enforcement with 429 responses.

This test suite focuses on integration scenarios where quota enforcement
triggers 429 (Too Many Requests) responses, including Redis integration
and realistic service-level enforcement.

Task 12.2: Write tests for quota enforcement - 429 Response Integration
"""
import asyncio
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from registry.models.tenant_quotas import TenantQuotas


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing quota counters."""
    redis_mock = Mock()
    redis_mock.get = Mock()
    redis_mock.incr = Mock()
    redis_mock.expire = Mock()
    redis_mock.ttl = Mock()
    return redis_mock


@pytest.fixture
def sample_tenant_id():
    """Generate a sample tenant ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def quota_enforcement_service():
    """Mock quota enforcement service for integration testing."""

    class QuotaEnforcementService:
        def __init__(self, redis_client, quotas):
            self.redis = redis_client
            self.quotas = quotas

        async def check_api_quota(self, tenant_id, increment=True):
            """Check API quota and optionally increment counter."""
            key = f"api_quota:{tenant_id}:daily"
            current_count = self.redis.get(key)
            current_count = int(current_count) if current_count else 0

            if increment:
                current_count += 1
                self.redis.incr(key)
                if self.redis.ttl(key) == -1:  # Set expiry if not exists
                    self.redis.expire(key, 86400)  # 24 hours

            is_within_limit = self.quotas.is_within_api_limit(current_count)

            return {
                "allowed": is_within_limit,
                "current_count": current_count,
                "limit": self.quotas.max_api_calls_per_day,
                "remaining": max(0, self.quotas.max_api_calls_per_day - current_count),
                "reset_time": datetime.now(UTC) + timedelta(days=1),
            }

        async def check_user_quota(self, tenant_id, current_users):
            """Check user quota."""
            is_within_limit = self.quotas.is_within_user_limit(current_users)

            return {
                "allowed": is_within_limit,
                "current_count": current_users,
                "limit": self.quotas.max_users,
                "remaining": max(0, self.quotas.max_users - current_users),
                "usage_percentage": self.quotas.get_user_usage_percentage(current_users),
            }

        def generate_429_response(self, quota_type, quota_result):
            """Generate 429 response when quota is exceeded."""
            if quota_result["allowed"]:
                return None  # No 429 needed

            return {
                "status_code": 429,
                "headers": {
                    "Retry-After": self._calculate_retry_after(quota_type, quota_result),
                    "X-RateLimit-Limit": str(quota_result["limit"]),
                    "X-RateLimit-Remaining": str(quota_result["remaining"]),
                    "X-RateLimit-Reset": quota_result.get("reset_time", "").isoformat()
                    if quota_result.get("reset_time")
                    else "",
                    "Content-Type": "application/json",
                },
                "body": {
                    "error": "quota_exceeded",
                    "message": f'{quota_type.title()} quota exceeded. Limit: {quota_result["limit"]}, Current: {quota_result["current_count"]}',
                    "quota_type": quota_type,
                    "current_usage": quota_result["current_count"],
                    "limit": quota_result["limit"],
                    "remaining": quota_result["remaining"],
                    "retry_after_seconds": self._calculate_retry_after(quota_type, quota_result),
                },
            }

        def _calculate_retry_after(self, quota_type, quota_result):
            """Calculate retry-after value in seconds."""
            if quota_type == "api_calls":
                # For daily API quotas, retry after midnight (or specific time window)
                now = datetime.now(UTC)
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
                    days=1
                )
                return int((tomorrow - now).total_seconds())
            elif quota_type == "users":
                # For user quotas, this typically requires quota increase
                return 3600  # Suggest retry in 1 hour (may need quota upgrade)
            else:
                return 300  # Default 5 minutes for other quota types

    return QuotaEnforcementService


class TestAPICallQuota429Responses:
    """Test 429 responses for API call quota enforcement."""

    async def test_api_quota_429_response_generation(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test generation of 429 response when API quota is exceeded."""
        # Setup quotas with low limit for easy testing
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=100)
        service = quota_enforcement_service(mock_redis, quotas)

        # Mock Redis to return count at limit
        mock_redis.get.return_value = b"100"  # At limit
        mock_redis.incr.return_value = 101  # Would exceed after increment

        # Check quota (this should trigger 429)
        quota_result = await service.check_api_quota(sample_tenant_id)

        assert quota_result["allowed"] is False, "API request should be denied when quota exceeded"
        assert quota_result["current_count"] == 101, "Current count should reflect increment"
        assert quota_result["remaining"] == 0, "No remaining requests should be available"

        # Generate 429 response
        response_429 = service.generate_429_response("api_calls", quota_result)

        assert response_429 is not None, "429 response should be generated"
        assert response_429["status_code"] == 429, "Response should have 429 status code"

        # Verify headers
        headers = response_429["headers"]
        assert "Retry-After" in headers, "429 response should include Retry-After header"
        assert "X-RateLimit-Limit" in headers, "429 response should include rate limit"
        assert "X-RateLimit-Remaining" in headers, "429 response should include remaining count"
        assert headers["X-RateLimit-Limit"] == "100", "Rate limit header should match quota"
        assert headers["X-RateLimit-Remaining"] == "0", "Remaining should be 0"

        # Verify body
        body = response_429["body"]
        assert body["error"] == "quota_exceeded", "Error type should be quota_exceeded"
        assert "api_calls" in body["message"].lower(), "Error message should mention API calls"
        assert body["quota_type"] == "api_calls", "Quota type should be specified"
        assert body["current_usage"] == 101, "Current usage should be included"
        assert body["limit"] == 100, "Limit should be included"

    async def test_api_quota_redis_counter_integration(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test Redis counter integration for API quota enforcement."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=50)
        service = quota_enforcement_service(mock_redis, quotas)

        # Simulate progressive API calls hitting the limit
        test_scenarios = [
            (b"0", 1, True),  # First call - allowed
            (b"10", 11, True),  # 11th call - allowed
            (b"25", 26, True),  # 26th call - allowed
            (b"49", 50, True),  # 50th call - allowed (at limit)
            (b"50", 51, False),  # 51st call - denied (over limit)
            (b"75", 76, False),  # 76th call - denied (way over)
        ]

        for redis_value, expected_count, should_allow in test_scenarios:
            mock_redis.get.return_value = redis_value
            mock_redis.incr.return_value = expected_count

            quota_result = await service.check_api_quota(sample_tenant_id)

            assert (
                quota_result["allowed"] == should_allow
            ), f"API call {expected_count} should be {'allowed' if should_allow else 'denied'}"
            assert (
                quota_result["current_count"] == expected_count
            ), f"Count should be {expected_count}"

            # Verify Redis interactions
            mock_redis.get.assert_called_with(f"api_quota:{sample_tenant_id}:daily")
            mock_redis.incr.assert_called_with(f"api_quota:{sample_tenant_id}:daily")

    async def test_api_quota_429_retry_after_calculation(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test accurate Retry-After calculation in 429 responses for API quotas."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=10)
        service = quota_enforcement_service(mock_redis, quotas)

        # Setup over-limit scenario
        mock_redis.get.return_value = b"10"
        mock_redis.incr.return_value = 11

        quota_result = await service.check_api_quota(sample_tenant_id)
        response_429 = service.generate_429_response("api_calls", quota_result)

        retry_after = int(response_429["headers"]["Retry-After"])

        # Retry-After for daily API quotas should be reasonable (up to 24 hours)
        assert (
            0 < retry_after <= 86400
        ), f"Retry-After should be between 0 and 86400 seconds, got {retry_after}"

        # Should also be included in response body
        assert (
            response_429["body"]["retry_after_seconds"] == retry_after
        ), "Retry-After in body should match header"

    async def test_api_quota_concurrent_requests_429(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test 429 responses with concurrent API requests hitting quota."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=20)
        service = quota_enforcement_service(mock_redis, quotas)

        # Simulate concurrent requests at the boundary
        async def make_concurrent_request(request_num):
            # Setup Redis to show we're near/at limit
            mock_redis.get.return_value = b"19"  # Just under limit
            mock_redis.incr.return_value = 20 + request_num  # Sequential increments

            return await service.check_api_quota(sample_tenant_id)

        # Make concurrent requests
        tasks = [make_concurrent_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Some requests should be allowed, others denied
        [r for r in results if r["allowed"]]
        allowed_results = [r for r in results if r["allowed"]]
        denied_results = [r for r in results if not r["allowed"]]

        # In this simulation, later requests should be denied
        assert len(denied_results) > 0, "Some concurrent requests should be denied"

        # Generate 429 responses for denied requests
        for result in denied_results:
            response_429 = service.generate_429_response("api_calls", result)
            assert response_429 is not None, "Denied requests should generate 429 responses"
            assert response_429["status_code"] == 429, "Response should be 429"


class TestUserQuota429Responses:
    """Test 429 responses for user quota enforcement."""

    async def test_user_quota_429_response_generation(
        self, sample_tenant_id, quota_enforcement_service
    ):
        """Test generation of 429 response when user quota is exceeded."""
        # Setup quotas with low user limit
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_users=5)
        service = quota_enforcement_service(None, quotas)  # No Redis needed for user quota

        # Test scenario where user creation would exceed quota
        current_users = 6  # Over the limit of 5

        quota_result = await service.check_user_quota(sample_tenant_id, current_users)

        assert (
            quota_result["allowed"] is False
        ), "User creation should be denied when quota exceeded"
        assert quota_result["current_count"] == 6, "Current count should be 6"
        assert quota_result["remaining"] == 0, "No remaining user slots"
        assert quota_result["usage_percentage"] == 120.0, "Usage should be 120%"

        # Generate 429 response
        response_429 = service.generate_429_response("users", quota_result)

        assert response_429 is not None, "429 response should be generated for user quota"
        assert response_429["status_code"] == 429, "Status should be 429"

        # Verify response content
        body = response_429["body"]
        assert body["quota_type"] == "users", "Quota type should be users"
        assert body["current_usage"] == 6, "Current usage should be included"
        assert body["limit"] == 5, "Limit should be included"
        assert "user" in body["message"].lower(), "Message should mention users"

    async def test_user_quota_429_at_boundary(self, sample_tenant_id, quota_enforcement_service):
        """Test 429 response behavior at user quota boundary."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_users=10)
        service = quota_enforcement_service(None, quotas)

        # Test at exact limit (should be allowed)
        quota_result_at_limit = await service.check_user_quota(sample_tenant_id, 10)
        response_at_limit = service.generate_429_response("users", quota_result_at_limit)

        assert quota_result_at_limit["allowed"] is True, "At limit should be allowed"
        assert response_at_limit is None, "No 429 response at limit"

        # Test over limit (should be denied with 429)
        quota_result_over_limit = await service.check_user_quota(sample_tenant_id, 11)
        response_over_limit = service.generate_429_response("users", quota_result_over_limit)

        assert quota_result_over_limit["allowed"] is False, "Over limit should be denied"
        assert response_over_limit is not None, "429 response should be generated over limit"
        assert (
            response_over_limit["body"]["current_usage"] == 11
        ), "Current usage should reflect over-limit"

    async def test_user_quota_429_retry_after_user_quota(
        self, sample_tenant_id, quota_enforcement_service
    ):
        """Test Retry-After calculation for user quota 429 responses."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_users=3)
        service = quota_enforcement_service(None, quotas)

        # Exceed user quota
        quota_result = await service.check_user_quota(sample_tenant_id, 4)
        response_429 = service.generate_429_response("users", quota_result)

        retry_after = int(response_429["headers"]["Retry-After"])

        # User quota retry should suggest waiting for potential quota upgrade
        assert retry_after > 0, "Retry-After should be positive"
        # Typically 1 hour (3600 seconds) for user quota issues
        assert retry_after >= 3600, "User quota retry should suggest substantial wait time"


class Test429ResponseIntegration:
    """Integration tests for 429 responses across different quota types."""

    async def test_multiple_quota_types_429_consistency(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test that 429 responses are consistent across different quota types."""
        # Setup quotas with low limits across all types
        quotas = TenantQuotas(
            tenant_id=sample_tenant_id,
            max_users=2,
            max_api_calls_per_day=5,
            max_storage_mb=10,
            max_records_per_model=100,
        )
        service = quota_enforcement_service(mock_redis, quotas)

        # Test API quota 429
        mock_redis.get.return_value = b"5"
        mock_redis.incr.return_value = 6
        api_quota_result = await service.check_api_quota(sample_tenant_id)
        api_429 = service.generate_429_response("api_calls", api_quota_result)

        # Test user quota 429
        user_quota_result = await service.check_user_quota(sample_tenant_id, 3)
        user_429 = service.generate_429_response("users", user_quota_result)

        # Verify consistent structure
        for response in [api_429, user_429]:
            assert response["status_code"] == 429, "All quota 429s should have same status code"
            assert "Retry-After" in response["headers"], "All should have Retry-After header"
            assert "error" in response["body"], "All should have error field"
            assert "quota_type" in response["body"], "All should specify quota type"
            assert "current_usage" in response["body"], "All should include current usage"
            assert "limit" in response["body"], "All should include limit"

    async def test_429_response_json_serialization(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test that 429 response bodies are properly JSON serializable."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=10)
        service = quota_enforcement_service(mock_redis, quotas)

        # Generate 429 response
        mock_redis.get.return_value = b"10"
        mock_redis.incr.return_value = 11
        quota_result = await service.check_api_quota(sample_tenant_id)
        response_429 = service.generate_429_response("api_calls", quota_result)

        # Test JSON serialization
        try:
            json_body = json.dumps(response_429["body"])
            parsed_back = json.loads(json_body)

            assert (
                parsed_back["error"] == "quota_exceeded"
            ), "JSON serialization should preserve data"
            assert parsed_back["current_usage"] == 11, "Numeric values should be preserved"
            assert parsed_back["quota_type"] == "api_calls", "String values should be preserved"

        except (TypeError, ValueError) as e:
            pytest.fail(f"429 response body should be JSON serializable: {e}")

    async def test_429_response_includes_helpful_information(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test that 429 responses include helpful information for developers."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=25)
        service = quota_enforcement_service(mock_redis, quotas)

        # Setup over-limit scenario
        mock_redis.get.return_value = b"25"
        mock_redis.incr.return_value = 26
        quota_result = await service.check_api_quota(sample_tenant_id)
        response_429 = service.generate_429_response("api_calls", quota_result)

        body = response_429["body"]

        # Check for helpful developer information
        assert "message" in body, "Should include human-readable message"
        assert len(body["message"]) > 20, "Message should be descriptive"
        assert str(body["limit"]) in body["message"], "Message should include limit"

        assert "quota_type" in body, "Should specify which quota was exceeded"
        assert "current_usage" in body, "Should show current usage"
        assert "remaining" in body, "Should show remaining quota (should be 0)"
        assert "retry_after_seconds" in body, "Should provide retry timing"

        # Verify values make sense
        assert body["remaining"] == 0, "Remaining should be 0 when over limit"
        assert body["current_usage"] > body["limit"], "Current usage should exceed limit"

    async def test_429_response_headers_comply_with_standards(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test that 429 response headers comply with HTTP standards."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=15)
        service = quota_enforcement_service(mock_redis, quotas)

        # Generate 429 response
        mock_redis.get.return_value = b"15"
        mock_redis.incr.return_value = 16
        quota_result = await service.check_api_quota(sample_tenant_id)
        response_429 = service.generate_429_response("api_calls", quota_result)

        headers = response_429["headers"]

        # Standard HTTP headers for rate limiting
        assert "Retry-After" in headers, "Must include Retry-After header (RFC 6585)"
        assert "Content-Type" in headers, "Must specify content type"
        assert headers["Content-Type"] == "application/json", "Should be JSON content type"

        # Rate limiting extension headers
        assert "X-RateLimit-Limit" in headers, "Should include rate limit"
        assert "X-RateLimit-Remaining" in headers, "Should include remaining count"

        # Verify header values are valid
        retry_after = headers["Retry-After"]
        assert retry_after.isdigit(), "Retry-After should be numeric"
        assert int(retry_after) > 0, "Retry-After should be positive"

        rate_limit = headers["X-RateLimit-Limit"]
        assert rate_limit.isdigit(), "Rate limit should be numeric"
        assert int(rate_limit) == 15, "Rate limit should match quota"

        remaining = headers["X-RateLimit-Remaining"]
        assert remaining.isdigit(), "Remaining should be numeric"
        assert int(remaining) == 0, "Remaining should be 0 when over quota"

    async def test_429_response_performance_under_load(
        self, mock_redis, sample_tenant_id, quota_enforcement_service
    ):
        """Test 429 response generation performance under load scenarios."""
        quotas = TenantQuotas(tenant_id=sample_tenant_id, max_api_calls_per_day=100)
        service = quota_enforcement_service(mock_redis, quotas)

        # Setup over-limit scenario
        mock_redis.get.return_value = b"100"
        mock_redis.incr.return_value = 101

        # Measure time to generate multiple 429 responses
        start_time = time.time()

        responses = []
        for _ in range(100):  # Generate 100 429 responses
            quota_result = await service.check_api_quota(sample_tenant_id)
            response_429 = service.generate_429_response("api_calls", quota_result)
            responses.append(response_429)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert (
            total_time < 1.0
        ), f"Generating 100 429 responses should take <1 second, took {total_time:.3f}s"
        assert len(responses) == 100, "Should generate exactly 100 responses"

        # Verify all responses are consistent
        for response in responses:
            assert response["status_code"] == 429, "All responses should be 429"
            assert "Retry-After" in response["headers"], "All should have Retry-After"
            assert (
                response["body"]["quota_type"] == "api_calls"
            ), "All should specify same quota type"

    async def test_429_response_with_quota_tier_differences(
        self, mock_redis, quota_enforcement_service
    ):
        """Test that 429 responses reflect different quota tiers appropriately."""
        tenant_ids = [str(uuid.uuid4()) for _ in range(3)]

        # Different quota tiers
        startup_quotas = TenantQuotas.create_startup_quotas(tenant_ids[0])  # 10K API calls
        default_quotas = TenantQuotas.create_default_quotas(tenant_ids[1])  # 100K API calls
        enterprise_quotas = TenantQuotas.create_enterprise_quotas(tenant_ids[2])  # 1M API calls

        quota_tiers = [
            ("startup", startup_quotas, tenant_ids[0]),
            ("default", default_quotas, tenant_ids[1]),
            ("enterprise", enterprise_quotas, tenant_ids[2]),
        ]

        for tier_name, quotas, tenant_id in quota_tiers:
            service = quota_enforcement_service(mock_redis, quotas)

            # Setup over-limit for each tier
            mock_redis.get.return_value = str(quotas.max_api_calls_per_day).encode()
            mock_redis.incr.return_value = quotas.max_api_calls_per_day + 1

            quota_result = await service.check_api_quota(tenant_id)
            response_429 = service.generate_429_response("api_calls", quota_result)

            # Verify 429 response reflects the correct tier limits
            assert (
                response_429["body"]["limit"] == quotas.max_api_calls_per_day
            ), f"{tier_name} tier 429 should reflect correct limit"

            # Verify Retry-After is reasonable for the tier
            retry_after = int(response_429["headers"]["Retry-After"])
            assert 0 < retry_after <= 86400, f"{tier_name} tier Retry-After should be reasonable"
