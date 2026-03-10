#!/usr/bin/env python3
"""Simple test to verify imports work."""
import os
import sys

# Add models to Python path
project_root = os.path.join(os.path.dirname(__file__), "..", "..")
models_path = os.path.join(project_root, "sdk", "venturestrat-models", "src")
sys.path.insert(0, models_path)

print(f"Testing imports from: {models_path}")

try:
    from registry.models.tenant_quotas import TenantQuotas

    print("✓ TenantQuotas import successful")
except ImportError as e:
    print(f"✗ TenantQuotas import failed: {e}")

try:
    from registry.middleware.quota import QuotaExceededException, RedisQuotaManager

    print("✓ QuotaMiddleware imports successful")
except ImportError as e:
    print(f"✗ QuotaMiddleware imports failed: {e}")

try:
    import redis.asyncio as redis

    print("✓ Redis import successful")
except ImportError as e:
    print(f"✗ Redis import failed: {e}")

# Test tenant quotas creation
try:
    tenant_id = "test-tenant-123"
    quotas = TenantQuotas(
        tenant_id=tenant_id,
        max_api_calls_per_day=5,
        max_users=3,
        max_storage_mb=10,
        max_records_per_model=50,
    )
    print(f"✓ TenantQuotas creation successful: {quotas.max_api_calls_per_day} API calls per day")
except Exception as e:
    print(f"✗ TenantQuotas creation failed: {e}")

print("Import test complete!")
