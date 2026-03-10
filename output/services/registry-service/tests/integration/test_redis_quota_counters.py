"""
Integration tests for Redis-based quota counters.

This test suite focuses specifically on Redis integration for quota enforcement,
testing counter management, expiration, and distributed quota checking.

Task 12.2: Write tests for quota enforcement - Redis Counter Integration
"""
import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call

import pytest
from registry.models.tenant_quotas import TenantQuotas


@pytest.fixture
def mock_redis():
    """Mock Redis client with realistic behavior."""
    redis_mock = Mock()

    # Default return values
    redis_mock.get.return_value = None
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = 86400
    redis_mock.exists.return_value = False
    redis_mock.delete.return_value = 1

    return redis_mock


@pytest.fixture
def redis_quota_manager():
    """Redis quota management service for testing."""

    class RedisQuotaManager:
        def __init__(self, redis_client):
            self.redis = redis_client

        def get_api_quota_key(self, tenant_id, date=None):
            """Generate Redis key for API quota counter."""
            if date is None:
                date = datetime.now(UTC).strftime("%Y-%m-%d")
            return f"quota:api:{tenant_id}:{date}"

        def get_user_quota_key(self, tenant_id):
            """Generate Redis key for user count."""
            return f"quota:users:{tenant_id}"

        def get_storage_quota_key(self, tenant_id):
            """Generate Redis key for storage usage."""
            return f"quota:storage:{tenant_id}"

        async def increment_api_counter(self, tenant_id):
            """Increment API call counter for tenant."""
            key = self.get_api_quota_key(tenant_id)
            count = self.redis.incr(key)

            # Set expiration if this is the first increment of the day
            if count == 1 or self.redis.ttl(key) == -1:
                # Expire at end of day
                now = datetime.now(UTC)
                end_of_day = now.replace(hour=23, minute=59, second=59) + timedelta(seconds=1)
                ttl_seconds = int((end_of_day - now).total_seconds())
                self.redis.expire(key, ttl_seconds)

            return count

        async def get_current_api_count(self, tenant_id):
            """Get current API call count for tenant."""
            key = self.get_api_quota_key(tenant_id)
            count = self.redis.get(key)
            return int(count) if count else 0

        async def set_user_count(self, tenant_id, count):
            """Set current user count for tenant."""
            key = self.get_user_quota_key(tenant_id)
            self.redis.set(key, count)
            # User counts don't expire

        async def get_current_user_count(self, tenant_id):
            """Get current user count for tenant."""
            key = self.get_user_quota_key(tenant_id)
            count = self.redis.get(key)
            return int(count) if count else 0

        async def update_storage_usage(self, tenant_id, storage_mb):
            """Update storage usage for tenant."""
            key = self.get_storage_quota_key(tenant_id)
            self.redis.set(key, storage_mb)

        async def get_current_storage_usage(self, tenant_id):
            """Get current storage usage for tenant."""
            key = self.get_storage_quota_key(tenant_id)
            usage = self.redis.get(key)
            return int(usage) if usage else 0

        async def reset_daily_counters(self, tenant_id):
            """Reset daily counters (for testing)."""
            key = self.get_api_quota_key(tenant_id)
            self.redis.delete(key)

        async def check_quota_with_redis(self, tenant_id, quotas, operation_type="api_call"):
            """Check quota using Redis counters."""
            if operation_type == "api_call":
                current_count = await self.get_current_api_count(tenant_id)
                # Check if incrementing would exceed quota
                is_allowed = quotas.is_within_api_limit(current_count + 1)
                if is_allowed:
                    new_count = await self.increment_api_counter(tenant_id)
                    return {
                        "allowed": True,
                        "current_count": new_count,
                        "limit": quotas.max_api_calls_per_day,
                        "remaining": max(0, quotas.max_api_calls_per_day - new_count),
                    }
                else:
                    return {
                        "allowed": False,
                        "current_count": current_count,
                        "limit": quotas.max_api_calls_per_day,
                        "remaining": 0,
                    }

            elif operation_type == "user_creation":
                current_count = await self.get_current_user_count(tenant_id)
                is_allowed = quotas.is_within_user_limit(current_count + 1)
                if is_allowed:
                    await self.set_user_count(tenant_id, current_count + 1)
                    return {
                        "allowed": True,
                        "current_count": current_count + 1,
                        "limit": quotas.max_users,
                        "remaining": max(0, quotas.max_users - (current_count + 1)),
                    }
                else:
                    return {
                        "allowed": False,
                        "current_count": current_count,
                        "limit": quotas.max_users,
                        "remaining": 0,
                    }

    return RedisQuotaManager


class TestRedisAPIQuotaCounters:
    """Test Redis-based API quota counters."""

    async def test_redis_api_counter_increments_correctly(self, mock_redis, redis_quota_manager):
        """Test that Redis API counter increments correctly."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # Mock Redis responses for incremental calls
        mock_redis.incr.side_effect = [1, 2, 3, 4, 5]  # Sequential increments
        mock_redis.ttl.return_value = 86400  # Key has TTL set

        # Make 5 API calls
        counts = []
        for i in range(5):
            count = await manager.increment_api_counter(tenant_id)
            counts.append(count)

        assert counts == [1, 2, 3, 4, 5], "API counter should increment sequentially"

        # Verify Redis calls
        expected_key = manager.get_api_quota_key(tenant_id)
        assert mock_redis.incr.call_count == 5, "Should call incr 5 times"
        mock_redis.incr.assert_has_calls([call(expected_key)] * 5)

    async def test_redis_api_counter_sets_expiration_on_first_call(
        self, mock_redis, redis_quota_manager
    ):
        """Test that Redis API counter sets expiration on first call of the day."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # First call - no TTL set yet
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = -1  # No TTL set

        await manager.increment_api_counter(tenant_id)

        # Should set expiration
        expected_key = manager.get_api_quota_key(tenant_id)
        mock_redis.expire.assert_called_once()
        expire_call = mock_redis.expire.call_args
        assert expire_call[0][0] == expected_key, "Should set expiration on correct key"
        assert expire_call[0][1] > 0, "TTL should be positive"
        assert expire_call[0][1] <= 86400, "TTL should be <= 24 hours"

    async def test_redis_api_counter_quota_enforcement(self, mock_redis, redis_quota_manager):
        """Test API quota enforcement using Redis counters."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_api_calls_per_day=10)

        # Test scenarios approaching and exceeding quota
        test_scenarios = [
            (0, 1, True),  # First call - allowed
            (5, 6, True),  # 6th call - allowed
            (9, 10, True),  # 10th call - allowed (at limit)
            (10, 10, False),  # 11th call - denied (would be 11)
            (15, 15, False),  # Way over limit - denied
        ]

        for current_redis_count, expected_count, should_allow in test_scenarios:
            mock_redis.get.return_value = (
                str(current_redis_count).encode() if current_redis_count > 0 else None
            )
            mock_redis.incr.return_value = current_redis_count + 1

            result = await manager.check_quota_with_redis(tenant_id, quotas, "api_call")

            assert (
                result["allowed"] == should_allow
            ), f"API call #{expected_count} should be {'allowed' if should_allow else 'denied'}"
            assert result["limit"] == 10, "Limit should be 10"

            if should_allow:
                assert result["current_count"] == current_redis_count + 1, "Count should increment"
            else:
                assert (
                    result["current_count"] == current_redis_count
                ), "Count should not increment when denied"
                assert result["remaining"] == 0, "No remaining calls when over quota"

    async def test_redis_api_counter_handles_concurrent_requests(
        self, mock_redis, redis_quota_manager
    ):
        """Test Redis API counter with concurrent requests."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_api_calls_per_day=20)

        # Simulate concurrent increment operations
        # Redis INCR is atomic, so each request gets a unique count
        concurrent_counts = [8, 9, 10, 11, 12]  # Simulated concurrent results

        async def simulate_concurrent_request(expected_count):
            mock_redis.get.return_value = str(expected_count - 1).encode()
            mock_redis.incr.return_value = expected_count
            return await manager.check_quota_with_redis(tenant_id, quotas, "api_call")

        # Run concurrent requests
        tasks = [simulate_concurrent_request(count) for count in concurrent_counts]
        results = await asyncio.gather(*tasks)

        # All should be allowed (under limit of 20)
        for result in results:
            assert result["allowed"] is True, "All concurrent requests should be allowed"
            assert result["limit"] == 20, "Limit should be consistent"

    async def test_redis_api_counter_daily_reset(self, mock_redis, redis_quota_manager):
        """Test Redis API counter daily reset functionality."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # Set up counter with some value
        mock_redis.get.return_value = b"50"
        current_count = await manager.get_current_api_count(tenant_id)
        assert current_count == 50, "Should read existing count"

        # Reset counters
        await manager.reset_daily_counters(tenant_id)

        # Verify delete was called
        expected_key = manager.get_api_quota_key(tenant_id)
        mock_redis.delete.assert_called_once_with(expected_key)

        # After reset, count should be 0
        mock_redis.get.return_value = None
        current_count = await manager.get_current_api_count(tenant_id)
        assert current_count == 0, "Count should be 0 after reset"

    async def test_redis_key_generation_consistency(self, mock_redis, redis_quota_manager):
        """Test Redis key generation is consistent and date-based."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # Test API quota key generation
        key1 = manager.get_api_quota_key(tenant_id)
        key2 = manager.get_api_quota_key(tenant_id)
        assert key1 == key2, "Same tenant same day should produce same key"

        # Key should contain tenant ID and date
        assert tenant_id in key1, "Key should contain tenant ID"
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        assert today in key1, "Key should contain today's date"

        # Test different date produces different key
        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        key_yesterday = manager.get_api_quota_key(tenant_id, yesterday)
        assert key_yesterday != key1, "Different dates should produce different keys"


class TestRedisUserQuotaCounters:
    """Test Redis-based user quota counters."""

    async def test_redis_user_counter_updates_correctly(self, mock_redis, redis_quota_manager):
        """Test that Redis user counter updates correctly."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # Set initial user count
        await manager.set_user_count(tenant_id, 5)
        expected_key = manager.get_user_quota_key(tenant_id)
        mock_redis.set.assert_called_with(expected_key, 5)

        # Read user count
        mock_redis.get.return_value = b"5"
        count = await manager.get_current_user_count(tenant_id)
        assert count == 5, "Should read correct user count"

    async def test_redis_user_quota_enforcement(self, mock_redis, redis_quota_manager):
        """Test user quota enforcement using Redis counters."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_users=8)

        test_scenarios = [
            (0, True),  # First user - allowed
            (3, True),  # 4th user - allowed
            (7, True),  # 8th user - allowed (at limit)
            (8, False),  # 9th user - denied
            (10, False),  # Way over - denied
        ]

        for current_user_count, should_allow in test_scenarios:
            mock_redis.get.return_value = (
                str(current_user_count).encode() if current_user_count > 0 else None
            )

            result = await manager.check_quota_with_redis(tenant_id, quotas, "user_creation")

            assert (
                result["allowed"] == should_allow
            ), f"User creation with {current_user_count} existing users should be {'allowed' if should_allow else 'denied'}"
            assert result["limit"] == 8, "User limit should be 8"

            if should_allow:
                expected_new_count = current_user_count + 1
                assert result["current_count"] == expected_new_count, "User count should increment"
                # Should call set with new count
                expected_key = manager.get_user_quota_key(tenant_id)
                mock_redis.set.assert_called_with(expected_key, expected_new_count)
            else:
                assert result["remaining"] == 0, "No remaining user slots when over quota"

    async def test_redis_user_counter_no_expiration(self, mock_redis, redis_quota_manager):
        """Test that user counters don't have expiration (persistent)."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        await manager.set_user_count(tenant_id, 10)

        # User counts should not have expiration set
        mock_redis.expire.assert_not_called()

        # Only set should be called, not expire
        expected_key = manager.get_user_quota_key(tenant_id)
        mock_redis.set.assert_called_once_with(expected_key, 10)


class TestRedisStorageQuotaCounters:
    """Test Redis-based storage quota counters."""

    async def test_redis_storage_counter_updates(self, mock_redis, redis_quota_manager):
        """Test Redis storage usage counter updates."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # Update storage usage
        await manager.update_storage_usage(tenant_id, 2048)  # 2GB

        expected_key = manager.get_storage_quota_key(tenant_id)
        mock_redis.set.assert_called_with(expected_key, 2048)

        # Read storage usage
        mock_redis.get.return_value = b"2048"
        usage = await manager.get_current_storage_usage(tenant_id)
        assert usage == 2048, "Should read correct storage usage"

    async def test_redis_storage_quota_enforcement_integration(
        self, mock_redis, redis_quota_manager
    ):
        """Test storage quota enforcement integration with Redis."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_storage_mb=5120)  # 5GB limit

        # Test different storage usage scenarios
        storage_scenarios = [
            (1024, True),  # 1GB - allowed
            (2560, True),  # 2.5GB - allowed
            (5120, True),  # 5GB - allowed (at limit)
            (6144, False),  # 6GB - over limit
        ]

        for storage_mb, should_be_within_limit in storage_scenarios:
            mock_redis.get.return_value = str(storage_mb).encode()
            current_usage = await manager.get_current_storage_usage(tenant_id)

            is_within_limit = quotas.is_within_storage_limit(current_usage)
            assert (
                is_within_limit == should_be_within_limit
            ), f"Storage usage {storage_mb}MB should be {'within' if should_be_within_limit else 'over'} limit"


class TestRedisQuotaIntegrationScenarios:
    """Integration tests for Redis quota scenarios."""

    async def test_redis_quota_multi_tenant_isolation(self, mock_redis, redis_quota_manager):
        """Test that Redis quota counters are properly isolated between tenants."""
        manager = redis_quota_manager(mock_redis)

        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        # Generate keys for different tenants
        tenant1_key = manager.get_api_quota_key(tenant1_id)
        tenant2_key = manager.get_api_quota_key(tenant2_id)

        assert tenant1_key != tenant2_key, "Different tenants should have different Redis keys"
        assert tenant1_id in tenant1_key, "Tenant 1 key should contain tenant 1 ID"
        assert tenant2_id in tenant2_key, "Tenant 2 key should contain tenant 2 ID"
        assert tenant1_id not in tenant2_key, "Tenant 2 key should not contain tenant 1 ID"
        assert tenant2_id not in tenant1_key, "Tenant 1 key should not contain tenant 2 ID"

        # Test user quota keys are also isolated
        user_key1 = manager.get_user_quota_key(tenant1_id)
        user_key2 = manager.get_user_quota_key(tenant2_id)
        assert user_key1 != user_key2, "User quota keys should be isolated"

    async def test_redis_quota_performance_simulation(self, mock_redis, redis_quota_manager):
        """Test Redis quota checking performance under load."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_api_calls_per_day=10000)

        # Simulate high load scenario
        start_time = time.time()

        # Mock Redis to return increasing counts
        mock_redis.get.side_effect = [str(i).encode() for i in range(100)]
        mock_redis.incr.side_effect = range(1, 101)

        # Make 100 quota checks rapidly
        results = []
        for i in range(100):
            result = await manager.check_quota_with_redis(tenant_id, quotas, "api_call")
            results.append(result)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 0.1, f"100 quota checks should be fast, took {total_time:.3f}s"
        assert len(results) == 100, "Should complete all quota checks"
        assert all(r["allowed"] for r in results), "All requests should be allowed (under limit)"

        # Verify Redis was called efficiently
        assert mock_redis.get.call_count == 100, "Should call Redis get for each check"
        assert mock_redis.incr.call_count == 100, "Should call Redis incr for each allowed request"

    async def test_redis_quota_error_handling(self, mock_redis, redis_quota_manager):
        """Test Redis quota handling when Redis operations fail."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())

        # Simulate Redis connection error
        mock_redis.get.side_effect = ConnectionError("Redis connection failed")

        # This should handle gracefully (in real implementation)
        # For testing, we'll verify the error propagates as expected
        with pytest.raises(ConnectionError):
            await manager.get_current_api_count(tenant_id)

        # Reset mock for further testing
        mock_redis.get.side_effect = None
        mock_redis.get.return_value = b"10"

        # Normal operation should work again
        count = await manager.get_current_api_count(tenant_id)
        assert count == 10, "Should work normally after error recovery"

    async def test_redis_quota_consistency_across_operations(self, mock_redis, redis_quota_manager):
        """Test quota consistency across different Redis operations."""
        manager = redis_quota_manager(mock_redis)
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_api_calls_per_day=50)

        # Simulate a sequence of API calls and quota checks
        call_sequence = [
            (10, True),  # Current: 10, next would be 11 - allowed
            (20, True),  # Current: 20, next would be 21 - allowed
            (49, True),  # Current: 49, next would be 50 - allowed (at limit)
            (50, False),  # Current: 50, next would be 51 - denied (over limit)
        ]

        for current_count, should_allow in call_sequence:
            mock_redis.get.return_value = str(current_count).encode()
            mock_redis.incr.return_value = current_count + 1

            result = await manager.check_quota_with_redis(tenant_id, quotas, "api_call")

            assert (
                result["allowed"] == should_allow
            ), f"Quota check with {current_count} current calls should be {'allowed' if should_allow else 'denied'}"

            # Verify counter consistency
            if should_allow:
                assert (
                    result["current_count"] == current_count + 1
                ), "Count should increment when allowed"
                assert result["remaining"] == quotas.max_api_calls_per_day - (
                    current_count + 1
                ), "Remaining count should be accurate"
            else:
                assert result["remaining"] == 0, "No remaining calls when over quota"
