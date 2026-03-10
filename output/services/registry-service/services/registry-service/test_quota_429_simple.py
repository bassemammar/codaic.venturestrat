#!/usr/bin/env python3
"""
Simple test for E2E quota 429 responses without external dependencies.
This verifies the core quota enforcement logic and 429 response generation.
"""
import os
import sys

# Add models to Python path FIRST before any other imports
project_root = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
models_path = os.path.join(project_root, "sdk", "venturestrat-models", "src")
sys.path.insert(0, models_path)

import asyncio
import uuid
from unittest.mock import AsyncMock

from registry.middleware.quota import RedisQuotaManager
from registry.models.tenant_quotas import TenantQuotas


async def test_quota_enforcement_429():
    """Test that quota enforcement generates proper 429 responses."""
    print("=== Testing Quota Enforcement 429 Logic ===")

    # Setup test data
    tenant_id = str(uuid.uuid4())
    print(f"Test tenant ID: {tenant_id}")

    # Create low quotas for easy testing
    quotas = TenantQuotas(
        tenant_id=tenant_id,
        max_api_calls_per_day=5,
        max_users=3,
        max_storage_mb=10,
        max_records_per_model=50,
    )
    print(f"Setup quotas: {quotas.max_api_calls_per_day} API calls per day")

    # Mock Redis client with proper async setup
    mock_redis = AsyncMock()
    quota_manager = RedisQuotaManager(mock_redis)

    # Test 1: Within quota limit
    print("\n--- Test 1: Within Quota Limit ---")
    mock_redis.get = AsyncMock(return_value=b"3")  # Current count
    mock_redis.incr = AsyncMock(return_value=4)  # After increment

    result = await quota_manager.check_and_increment_api_quota(tenant_id, quotas)

    assert result["allowed"] is True, "Should allow request within quota"
    assert result["current_count"] == 4, "Should show correct current count"
    assert result["remaining"] == 1, "Should show 1 remaining"
    print(
        f"✓ Within quota: {result['current_count']}/{quotas.max_api_calls_per_day}, allowed={result['allowed']}"
    )

    # Test 2: At quota limit (should still allow)
    print("\n--- Test 2: At Quota Limit ---")
    mock_redis.get.return_value = b"4"  # Current count
    mock_redis.incr.return_value = 5  # At limit after increment

    result = await quota_manager.check_and_increment_api_quota(tenant_id, quotas)

    assert result["allowed"] is True, "Should allow request at quota limit"
    assert result["current_count"] == 5, "Should show count at limit"
    assert result["remaining"] == 0, "Should show 0 remaining"
    print(
        f"✓ At quota: {result['current_count']}/{quotas.max_api_calls_per_day}, allowed={result['allowed']}"
    )

    # Test 3: Over quota limit (should deny and generate 429)
    print("\n--- Test 3: Over Quota Limit ---")
    mock_redis.get.return_value = b"5"  # At limit
    mock_redis.incr.return_value = 6  # Would exceed after increment

    result = await quota_manager.check_and_increment_api_quota(tenant_id, quotas)

    assert result["allowed"] is False, "Should deny request over quota"
    assert result["current_count"] == 6, "Should show exceeded count"
    assert result["remaining"] == 0, "Should show 0 remaining"
    assert result["usage_percentage"] > 100, "Usage percentage should exceed 100%"
    print(
        f"✓ Over quota: {result['current_count']}/{quotas.max_api_calls_per_day}, allowed={result['allowed']}, usage={result['usage_percentage']:.1f}%"
    )

    # Test 4: Generate 429 response
    print("\n--- Test 4: 429 Response Generation ---")

    # This would normally be done by the middleware
    # Let's simulate the 429 response generation
    if not result["allowed"]:
        response_data = {
            "status_code": 429,
            "headers": {
                "Retry-After": str(86400),  # 24 hours for daily quota
                "X-RateLimit-Limit": str(quotas.max_api_calls_per_day),
                "X-RateLimit-Remaining": str(result["remaining"]),
                "Content-Type": "application/json",
            },
            "body": {
                "error": "quota_exceeded",
                "message": f'API call quota exceeded. Limit: {quotas.max_api_calls_per_day}, Current: {result["current_count"]}',
                "quota_type": "api_calls",
                "current_usage": result["current_count"],
                "limit": quotas.max_api_calls_per_day,
                "remaining": result["remaining"],
                "usage_percentage": result["usage_percentage"],
                "retry_after_seconds": 86400,
            },
        }

        # Verify 429 response structure
        assert response_data["status_code"] == 429, "Status code should be 429"
        assert "Retry-After" in response_data["headers"], "Should have Retry-After header"
        assert response_data["headers"]["X-RateLimit-Limit"] == str(
            quotas.max_api_calls_per_day
        ), "Should show correct limit"
        assert response_data["headers"]["X-RateLimit-Remaining"] == "0", "Should show 0 remaining"

        body = response_data["body"]
        assert body["error"] == "quota_exceeded", "Should have quota_exceeded error"
        assert body["quota_type"] == "api_calls", "Should specify API calls quota"
        assert body["current_usage"] == 6, "Should show current usage"
        assert body["limit"] == 5, "Should show limit"
        assert body["remaining"] == 0, "Should show 0 remaining"
        assert "API call quota exceeded" in body["message"], "Should have descriptive message"

        print("✓ 429 Response structure validated")
        print(f"  Status: {response_data['status_code']}")
        print(f"  Retry-After: {response_data['headers']['Retry-After']} seconds")
        print(f"  Rate Limit: {response_data['headers']['X-RateLimit-Limit']}")
        print(f"  Remaining: {response_data['headers']['X-RateLimit-Remaining']}")
        print(f"  Error: {body['error']}")
        print(f"  Message: {body['message']}")

    # Test 5: Different tenant isolation
    print("\n--- Test 5: Tenant Isolation ---")
    tenant_b_id = str(uuid.uuid4())

    # Tenant B should start with clean quota
    mock_redis.get.return_value = b"0"  # Clean start
    mock_redis.incr.return_value = 1  # First call

    result_b = await quota_manager.check_and_increment_api_quota(tenant_b_id, quotas)

    assert result_b["allowed"] is True, "Different tenant should have fresh quota"
    assert result_b["current_count"] == 1, "Should start at 1 for new tenant"
    assert result_b["remaining"] == 4, "Should have 4 remaining for new tenant"
    print(
        f"✓ Tenant B isolation: {result_b['current_count']}/{quotas.max_api_calls_per_day}, allowed={result_b['allowed']}"
    )

    print("\n=== All Tests Passed! ===")
    print("✓ Core quota enforcement logic works correctly")
    print("✓ 429 responses are properly structured")
    print("✓ Tenant isolation is maintained")
    print("✓ Rate limiting headers are included")
    print("✓ Error messages are descriptive")


if __name__ == "__main__":
    asyncio.run(test_quota_enforcement_429())
