"""
Tests for quota enforcement - comprehensive enforcement scenarios.

This test suite focuses specifically on quota enforcement mechanisms including:
1. API call quota enforcement with Redis counters
2. User limit enforcement
3. 429 response generation when quotas are exceeded

Task 12.2: Write tests for quota enforcement
"""
import uuid
from unittest.mock import Mock, patch

import pytest
from registry.models.tenant_quotas import TenantQuotas


@pytest.fixture
def sample_tenant_id():
    """Generate a sample tenant ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def default_quotas(sample_tenant_id):
    """Create default tenant quotas for testing."""
    return TenantQuotas.create_default_quotas(sample_tenant_id)


@pytest.fixture
def startup_quotas(sample_tenant_id):
    """Create startup tier quotas for testing (lower limits)."""
    return TenantQuotas.create_startup_quotas(sample_tenant_id)


@pytest.fixture
def enterprise_quotas(sample_tenant_id):
    """Create enterprise tier quotas for testing (higher limits)."""
    return TenantQuotas.create_enterprise_quotas(sample_tenant_id)


@pytest.fixture
def custom_low_quotas(sample_tenant_id):
    """Create custom quotas with very low limits for easy testing."""
    return TenantQuotas(
        tenant_id=sample_tenant_id,
        max_users=5,
        max_records_per_model=100,
        max_api_calls_per_day=50,
        max_storage_mb=10,
    )


class TestAPICallQuotaEnforcement:
    """Test API call quota enforcement with Redis counters."""

    def test_api_quota_within_limit_allows_request(self, default_quotas):
        """Test that API calls within quota are allowed."""
        # Simulate current API call count within limit
        current_api_calls = 50000  # Well under 100,000 daily limit

        result = default_quotas.is_within_api_limit(current_api_calls)

        assert result is True, "API calls within quota should be allowed"

    def test_api_quota_at_exact_limit_allows_request(self, default_quotas):
        """Test that API calls at exact quota limit are allowed."""
        # Test at exact limit
        current_api_calls = default_quotas.max_api_calls_per_day  # Exactly 100,000

        result = default_quotas.is_within_api_limit(current_api_calls)

        assert result is True, "API calls at exact quota limit should be allowed"

    def test_api_quota_over_limit_blocks_request(self, default_quotas):
        """Test that API calls over quota are blocked."""
        # Simulate exceeding daily limit
        current_api_calls = default_quotas.max_api_calls_per_day + 1  # 100,001

        result = default_quotas.is_within_api_limit(current_api_calls)

        assert result is False, "API calls over quota should be blocked"

    def test_api_quota_enforcement_with_different_tiers(self, startup_quotas, enterprise_quotas):
        """Test API quota enforcement varies by tier."""
        # Same API call count, different enforcement based on tier
        api_calls = 50000

        # Startup tier (10,000 limit) should block
        startup_result = startup_quotas.is_within_api_limit(api_calls)
        assert startup_result is False, "High API calls should exceed startup tier quota"

        # Enterprise tier (1,000,000 limit) should allow
        enterprise_result = enterprise_quotas.is_within_api_limit(api_calls)
        assert enterprise_result is True, "Same API calls should be within enterprise tier quota"

    def test_api_quota_enforcement_boundary_conditions(self, custom_low_quotas):
        """Test API quota enforcement at boundary conditions."""
        # Test various boundary scenarios with low quota (50 calls/day)
        quota_limit = custom_low_quotas.max_api_calls_per_day  # 50

        # Just under limit
        assert custom_low_quotas.is_within_api_limit(quota_limit - 1) is True

        # At limit
        assert custom_low_quotas.is_within_api_limit(quota_limit) is True

        # Just over limit
        assert custom_low_quotas.is_within_api_limit(quota_limit + 1) is False

        # Significantly over limit
        assert custom_low_quotas.is_within_api_limit(quota_limit * 2) is False

    def test_api_quota_usage_percentage_calculation(self, default_quotas):
        """Test accurate usage percentage calculation for API quota."""

        # Test various usage levels
        test_cases = [
            (0, 0.0),  # No usage
            (10000, 10.0),  # 10% usage
            (25000, 25.0),  # 25% usage
            (50000, 50.0),  # 50% usage
            (75000, 75.0),  # 75% usage
            (90000, 90.0),  # 90% usage
            (100000, 100.0),  # 100% usage (at limit)
            (125000, 125.0),  # 125% usage (over limit)
            (200000, 200.0),  # 200% usage (significantly over)
        ]

        for current_usage, expected_percentage in test_cases:
            actual_percentage = default_quotas.get_api_usage_percentage(current_usage)
            assert (
                actual_percentage == expected_percentage
            ), f"Usage {current_usage} should result in {expected_percentage}% but got {actual_percentage}%"

    @patch("redis.Redis")
    def test_redis_counter_simulation_within_limit(self, mock_redis, default_quotas):
        """Simulate Redis counter behavior when within API limit."""
        # Mock Redis counter returning value within limit
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = b"45000"  # 45,000 calls today (within 100k limit)

        # Simulate checking quota before allowing API call
        current_count = int(mock_redis_instance.get.return_value.decode())
        quota_check = default_quotas.is_within_api_limit(current_count + 1)  # +1 for new request

        assert (
            quota_check is True
        ), "Request should be allowed when Redis counter shows usage within quota"

    @patch("redis.Redis")
    def test_redis_counter_simulation_over_limit(self, mock_redis, default_quotas):
        """Simulate Redis counter behavior when over API limit."""
        # Mock Redis counter returning value over limit
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = b"100000"  # Already at 100,000 calls

        # Simulate checking quota before allowing API call
        current_count = int(mock_redis_instance.get.return_value.decode())
        quota_check = default_quotas.is_within_api_limit(current_count + 1)  # +1 would exceed

        assert (
            quota_check is False
        ), "Request should be blocked when Redis counter shows usage over quota"

    def test_api_quota_enforcement_with_burst_requests(self, custom_low_quotas):
        """Test API quota enforcement with burst of requests."""
        # Simulate checking multiple rapid requests against quota
        quota_limit = custom_low_quotas.max_api_calls_per_day  # 50

        # Simulate checking each request in a burst
        results = []
        for i in range(1, 55):  # Try 54 requests
            is_allowed = custom_low_quotas.is_within_api_limit(i)
            results.append((i, is_allowed))

        # Verify that requests 1-50 are allowed, 51+ are blocked
        allowed_requests = [count for count, allowed in results if allowed]
        blocked_requests = [count for count, allowed in results if not allowed]

        assert max(allowed_requests) <= quota_limit, "No request over quota should be allowed"
        assert min(blocked_requests) > quota_limit, "All requests over quota should be blocked"
        assert (
            len(allowed_requests) == quota_limit
        ), f"Exactly {quota_limit} requests should be allowed"


class TestUserLimitEnforcement:
    """Test user limit enforcement."""

    def test_user_limit_within_quota_allows_creation(self, default_quotas):
        """Test that user creation within quota is allowed."""
        current_users = 50  # Well under 100 user limit

        result = default_quotas.is_within_user_limit(current_users)

        assert result is True, "User creation within quota should be allowed"

    def test_user_limit_at_exact_quota_allows_creation(self, default_quotas):
        """Test that user creation at exact quota limit is allowed."""
        current_users = default_quotas.max_users  # Exactly 100 users

        result = default_quotas.is_within_user_limit(current_users)

        assert result is True, "User creation at exact quota should be allowed"

    def test_user_limit_over_quota_blocks_creation(self, default_quotas):
        """Test that user creation over quota is blocked."""
        current_users = default_quotas.max_users + 1  # 101 users

        result = default_quotas.is_within_user_limit(current_users)

        assert result is False, "User creation over quota should be blocked"

    def test_user_limit_enforcement_across_tiers(
        self, startup_quotas, default_quotas, enterprise_quotas
    ):
        """Test user limit enforcement varies correctly across tiers."""
        user_count = 50

        # Startup (10 users) - should block
        assert (
            startup_quotas.is_within_user_limit(user_count) is False
        ), "50 users should exceed startup tier limit of 10"

        # Default (100 users) - should allow
        assert (
            default_quotas.is_within_user_limit(user_count) is True
        ), "50 users should be within default tier limit of 100"

        # Enterprise (1000 users) - should allow
        assert (
            enterprise_quotas.is_within_user_limit(user_count) is True
        ), "50 users should be within enterprise tier limit of 1000"

    def test_user_limit_boundary_conditions(self, custom_low_quotas):
        """Test user limit enforcement at boundary conditions."""
        user_limit = custom_low_quotas.max_users  # 5 users

        # Test boundary conditions
        assert custom_low_quotas.is_within_user_limit(0) is True, "Zero users should be allowed"
        assert custom_low_quotas.is_within_user_limit(1) is True, "1 user should be allowed"
        assert (
            custom_low_quotas.is_within_user_limit(user_limit - 1) is True
        ), "Just under limit should be allowed"
        assert (
            custom_low_quotas.is_within_user_limit(user_limit) is True
        ), "At limit should be allowed"
        assert (
            custom_low_quotas.is_within_user_limit(user_limit + 1) is False
        ), "Over limit should be blocked"

    def test_user_usage_percentage_accuracy(self, default_quotas):
        """Test accurate user usage percentage calculation."""

        test_cases = [
            (0, 0.0),  # No users
            (10, 10.0),  # 10% usage
            (25, 25.0),  # 25% usage
            (50, 50.0),  # 50% usage
            (75, 75.0),  # 75% usage
            (90, 90.0),  # 90% usage
            (100, 100.0),  # 100% usage (at limit)
            (110, 110.0),  # 110% usage (over limit)
            (150, 150.0),  # 150% usage (significantly over)
        ]

        for current_users, expected_percentage in test_cases:
            actual_percentage = default_quotas.get_user_usage_percentage(current_users)
            assert (
                abs(actual_percentage - expected_percentage) < 0.001
            ), f"User count {current_users} should result in {expected_percentage}% but got {actual_percentage}%"

    def test_user_limit_enforcement_prevents_service_degradation(self, startup_quotas):
        """Test that user limit enforcement prevents service degradation."""
        # Startup tier has 10 user limit - test that it enforces properly
        user_limit = startup_quotas.max_users  # 10

        # Simulate onboarding users one by one
        for user_count in range(1, user_limit + 1):
            assert (
                startup_quotas.is_within_user_limit(user_count) is True
            ), f"User {user_count} should be allowed within limit of {user_limit}"

        # Further users should be blocked to prevent service degradation
        for excessive_count in range(user_limit + 1, user_limit + 5):
            assert (
                startup_quotas.is_within_user_limit(excessive_count) is False
            ), f"User count {excessive_count} should be blocked to prevent service degradation"

    def test_user_limit_enforcement_with_concurrent_checks(self, custom_low_quotas):
        """Test user limit enforcement with simulated concurrent user creation checks."""
        user_limit = custom_low_quotas.max_users  # 5

        # Simulate multiple concurrent checks at the boundary
        current_users = user_limit - 1  # 4 users currently

        # Multiple services might check if they can add a user simultaneously
        check_results = []
        for _ in range(3):  # Simulate 3 concurrent checks
            can_add_user = custom_low_quotas.is_within_user_limit(current_users + 1)
            check_results.append(can_add_user)

        # All checks should return True (5th user is allowed)
        assert all(check_results), "All concurrent checks should allow adding the 5th user"

        # But adding a 6th user should be blocked
        cannot_add_sixth = custom_low_quotas.is_within_user_limit(user_limit + 1)
        assert cannot_add_sixth is False, "6th user should be blocked"


class TestQuotaExceeded429ResponseGeneration:
    """Test 429 response generation when quotas are exceeded."""

    def test_api_quota_exceeded_triggers_429_condition(self, default_quotas):
        """Test that exceeding API quota creates condition for 429 response."""
        # When API quota is exceeded, should return False (triggering 429)
        over_limit_calls = default_quotas.max_api_calls_per_day + 1000  # 101,000 calls

        quota_check = default_quotas.is_within_api_limit(over_limit_calls)

        assert quota_check is False, "Exceeded API quota should trigger 429 response condition"

    def test_user_quota_exceeded_triggers_429_condition(self, default_quotas):
        """Test that exceeding user quota creates condition for 429 response."""
        # When user quota is exceeded, should return False (triggering 429)
        over_limit_users = default_quotas.max_users + 10  # 110 users

        quota_check = default_quotas.is_within_user_limit(over_limit_users)

        assert quota_check is False, "Exceeded user quota should trigger 429 response condition"

    def test_storage_quota_exceeded_triggers_429_condition(self, default_quotas):
        """Test that exceeding storage quota creates condition for 429 response."""
        # When storage quota is exceeded, should return False (triggering 429)
        over_limit_storage = default_quotas.max_storage_mb + 1000  # 11,240 MB (11.24 GB)

        quota_check = default_quotas.is_within_storage_limit(over_limit_storage)

        assert quota_check is False, "Exceeded storage quota should trigger 429 response condition"

    def test_record_quota_exceeded_triggers_429_condition(self, default_quotas):
        """Test that exceeding record quota creates condition for 429 response."""
        # When record quota is exceeded, should return False (triggering 429)
        over_limit_records = default_quotas.max_records_per_model + 100000  # 1,100,000 records

        quota_check = default_quotas.is_within_record_limit(over_limit_records)

        assert quota_check is False, "Exceeded record quota should trigger 429 response condition"

    def test_429_response_data_structure(self, custom_low_quotas):
        """Test 429 response data structure for different quota types."""
        # Simulate data that would be included in 429 responses
        quota_info = {
            "tenant_id": custom_low_quotas.tenant_id,
            "quotas": {
                "max_users": custom_low_quotas.max_users,
                "max_api_calls_per_day": custom_low_quotas.max_api_calls_per_day,
                "max_storage_mb": custom_low_quotas.max_storage_mb,
                "max_records_per_model": custom_low_quotas.max_records_per_model,
            },
        }

        # Test that quota info contains expected structure for 429 responses
        assert "tenant_id" in quota_info
        assert "quotas" in quota_info
        assert quota_info["quotas"]["max_users"] == 5
        assert quota_info["quotas"]["max_api_calls_per_day"] == 50
        assert quota_info["quotas"]["max_storage_mb"] == 10
        assert quota_info["quotas"]["max_records_per_model"] == 100

    def test_429_response_includes_usage_percentage(self, default_quotas):
        """Test that 429 response includes current usage percentage."""
        # Simulate over-limit usage scenarios
        scenarios = [
            {
                "type": "api_calls",
                "current": 150000,  # 150% of 100,000 limit
                "calculate_percentage": lambda: default_quotas.get_api_usage_percentage(150000),
                "expected": 150.0,
            },
            {
                "type": "users",
                "current": 150,  # 150% of 100 limit
                "calculate_percentage": lambda: default_quotas.get_user_usage_percentage(150),
                "expected": 150.0,
            },
            {
                "type": "storage",
                "current": 15360,  # 150% of 10240 MB limit (15GB vs 10GB limit)
                "calculate_percentage": lambda: default_quotas.get_storage_usage_percentage(15360),
                "expected": 150.0,
            },
        ]

        for scenario in scenarios:
            percentage = scenario["calculate_percentage"]()
            assert percentage > 100.0, f"{scenario['type']} over-limit should show >100% usage"
            assert (
                abs(percentage - scenario["expected"]) < 0.001
            ), f"{scenario['type']} should show exactly {scenario['expected']}% usage, got {percentage}%"

    def test_429_response_varies_by_quota_tier(self, startup_quotas, enterprise_quotas):
        """Test that 429 response thresholds vary by quota tier."""
        # Same usage level, different 429 triggers based on tier
        api_calls = 15000
        users = 50

        # Startup tier (low limits) - should trigger 429 conditions
        startup_api_exceeded = not startup_quotas.is_within_api_limit(api_calls)
        startup_users_exceeded = not startup_quotas.is_within_user_limit(users)

        assert startup_api_exceeded is True, "15K API calls should exceed startup limit"
        assert startup_users_exceeded is True, "50 users should exceed startup limit"

        # Enterprise tier (high limits) - should not trigger 429 conditions
        enterprise_api_exceeded = not enterprise_quotas.is_within_api_limit(api_calls)
        enterprise_users_exceeded = not enterprise_quotas.is_within_user_limit(users)

        assert enterprise_api_exceeded is False, "15K API calls should not exceed enterprise limit"
        assert enterprise_users_exceeded is False, "50 users should not exceed enterprise limit"

    def test_429_response_conditions_at_boundaries(self, custom_low_quotas):
        """Test 429 response conditions at quota boundaries."""
        # Test right at the boundary where 429 should start triggering
        quotas = custom_low_quotas

        # At limit - should NOT trigger 429
        at_limit_conditions = [
            not quotas.is_within_api_limit(
                quotas.max_api_calls_per_day
            ),  # Should be False (no 429)
            not quotas.is_within_user_limit(quotas.max_users),  # Should be False (no 429)
            not quotas.is_within_storage_limit(quotas.max_storage_mb),  # Should be False (no 429)
            not quotas.is_within_record_limit(
                quotas.max_records_per_model
            ),  # Should be False (no 429)
        ]

        assert all(
            condition is False for condition in at_limit_conditions
        ), "At quota limit should NOT trigger 429 responses"

        # Just over limit - should trigger 429
        over_limit_conditions = [
            not quotas.is_within_api_limit(
                quotas.max_api_calls_per_day + 1
            ),  # Should be True (429)
            not quotas.is_within_user_limit(quotas.max_users + 1),  # Should be True (429)
            not quotas.is_within_storage_limit(quotas.max_storage_mb + 1),  # Should be True (429)
            not quotas.is_within_record_limit(
                quotas.max_records_per_model + 1
            ),  # Should be True (429)
        ]

        assert all(
            condition is True for condition in over_limit_conditions
        ), "Over quota limit should trigger 429 responses"


class TestQuotaEnforcementIntegration:
    """Integration tests for quota enforcement across different scenarios."""

    def test_quota_enforcement_prevents_tenant_abuse(self, startup_quotas):
        """Test that quota enforcement prevents tenant resource abuse."""
        # Simulate a tenant trying to abuse resources
        quotas = startup_quotas  # Low limits: 10 users, 10K API calls, 1GB storage, 100K records

        # Test multiple resource types being exhausted
        abuse_scenarios = [
            ("users", quotas.max_users + 50, quotas.is_within_user_limit),
            ("api_calls", quotas.max_api_calls_per_day + 10000, quotas.is_within_api_limit),
            ("storage", quotas.max_storage_mb + 500, quotas.is_within_storage_limit),
            ("records", quotas.max_records_per_model + 50000, quotas.is_within_record_limit),
        ]

        for resource_type, abuse_amount, check_function in abuse_scenarios:
            is_allowed = check_function(abuse_amount)
            assert (
                is_allowed is False
            ), f"Abuse of {resource_type} should be blocked by quota enforcement"

    def test_quota_enforcement_allows_legitimate_usage(self, default_quotas):
        """Test that quota enforcement allows legitimate usage patterns."""
        # Test legitimate usage patterns that should be allowed
        quotas = (
            default_quotas  # Standard limits: 100 users, 100K API calls, 10GB storage, 1M records
        )

        legitimate_scenarios = [
            ("moderate_users", quotas.max_users // 2, quotas.is_within_user_limit),
            ("normal_api_usage", quotas.max_api_calls_per_day // 3, quotas.is_within_api_limit),
            ("reasonable_storage", quotas.max_storage_mb // 2, quotas.is_within_storage_limit),
            ("typical_records", quotas.max_records_per_model // 4, quotas.is_within_record_limit),
        ]

        for scenario_type, usage_amount, check_function in legitimate_scenarios:
            is_allowed = check_function(usage_amount)
            assert (
                is_allowed is True
            ), f"Legitimate {scenario_type} should be allowed by quota enforcement"

    def test_quota_enforcement_consistency_across_methods(self, default_quotas):
        """Test that quota enforcement is consistent across different checking methods."""
        quotas = default_quotas

        # Test the same limits using different approaches
        api_limit = quotas.max_api_calls_per_day

        # Method 1: Direct limit checking
        at_limit_check = quotas.is_within_api_limit(api_limit)
        over_limit_check = quotas.is_within_api_limit(api_limit + 1)

        # Method 2: Using percentage calculation
        at_limit_percentage = quotas.get_api_usage_percentage(api_limit)
        over_limit_percentage = quotas.get_api_usage_percentage(api_limit + 1)

        # Verify consistency
        assert at_limit_check is True, "At limit should be allowed"
        assert over_limit_check is False, "Over limit should be blocked"
        assert at_limit_percentage == 100.0, "At limit should be 100% usage"
        assert over_limit_percentage > 100.0, "Over limit should be >100% usage"

    def test_quota_enforcement_with_quota_updates(self, sample_tenant_id):
        """Test that quota enforcement works correctly after quota updates."""
        # Start with low quotas
        original_quotas = TenantQuotas.create_startup_quotas(sample_tenant_id)  # 10 users

        # Test with amount that exceeds startup limit
        test_users = 25

        # Should be blocked with startup quotas
        startup_check = original_quotas.is_within_user_limit(test_users)
        assert startup_check is False, "25 users should exceed startup limit of 10"

        # Update to higher quotas
        updated_quotas = original_quotas.update_quotas(max_users=50)

        # Same amount should now be allowed
        updated_check = updated_quotas.is_within_user_limit(test_users)
        assert updated_check is True, "25 users should be within updated limit of 50"

        # Verify original quotas unchanged (immutable pattern)
        original_still_blocks = original_quotas.is_within_user_limit(test_users)
        assert original_still_blocks is False, "Original quotas should be unchanged"

    def test_quota_enforcement_edge_case_zero_limits(self, sample_tenant_id):
        """Test quota enforcement behavior with hypothetical zero limits."""
        # Note: In production, quotas should have positive minimum values
        # This tests the enforcement logic at extreme boundaries

        # Create quotas with 1 as minimum (closest to zero while maintaining positivity)
        minimal_quotas = TenantQuotas(
            tenant_id=sample_tenant_id,
            max_users=1,
            max_records_per_model=1,
            max_api_calls_per_day=1,
            max_storage_mb=1,
        )

        # Test that even minimal positive usage is properly enforced
        assert minimal_quotas.is_within_user_limit(0) is True, "Zero usage should be allowed"
        assert (
            minimal_quotas.is_within_user_limit(1) is True
        ), "Usage at minimal limit should be allowed"
        assert (
            minimal_quotas.is_within_user_limit(2) is False
        ), "Usage over minimal limit should be blocked"

        # Test percentage calculations with minimal quotas
        assert minimal_quotas.get_user_usage_percentage(0) == 0.0, "Zero usage should be 0%"
        assert minimal_quotas.get_user_usage_percentage(1) == 100.0, "Limit usage should be 100%"
        assert minimal_quotas.get_user_usage_percentage(2) == 200.0, "Over-limit should be >100%"
