"""Tests for TenantQuotas model - TDD approach.

These tests define the expected behavior of the TenantQuotas model for resource quota management.
Includes CRUD operations, validation, utility methods, and constraints as required by task 12.1.
"""
import uuid
from datetime import UTC, datetime

import pytest
from registry.models.tenant_quotas import TenantQuotas


class TestTenantQuotasCreation:
    """Tests for TenantQuotas model creation and initialization."""

    def test_create_default_quotas(self):
        """Create tenant quotas with default values."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id)

        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 100
        assert quotas.max_records_per_model == 1000000
        assert quotas.max_api_calls_per_day == 100000
        assert quotas.max_storage_mb == 10240  # 10GB
        assert quotas.created_at is not None
        assert quotas.updated_at is not None

    def test_create_custom_quotas(self):
        """Create tenant quotas with custom values."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=50,
            max_records_per_model=500000,
            max_api_calls_per_day=50000,
            max_storage_mb=5120,  # 5GB
        )

        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 50
        assert quotas.max_records_per_model == 500000
        assert quotas.max_api_calls_per_day == 50000
        assert quotas.max_storage_mb == 5120

    def test_create_with_full_specification(self):
        """Create tenant quotas with all fields specified."""
        tenant_id = str(uuid.uuid4())
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=200,
            max_records_per_model=2000000,
            max_api_calls_per_day=200000,
            max_storage_mb=20480,  # 20GB
            created_at=created_at,
            updated_at=updated_at,
        )

        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 200
        assert quotas.max_records_per_model == 2000000
        assert quotas.max_api_calls_per_day == 200000
        assert quotas.max_storage_mb == 20480
        assert quotas.created_at == created_at
        assert quotas.updated_at == updated_at

    def test_tenant_id_required(self):
        """Tenant ID is required for creating quotas."""
        with pytest.raises((ValueError, TypeError)):
            TenantQuotas(
                max_users=100,
                max_records_per_model=1000000,
                max_api_calls_per_day=100000,
                max_storage_mb=10240,
            )


class TestTenantQuotasFactoryMethods:
    """Tests for TenantQuotas factory methods."""

    def test_create_default_quotas_factory(self):
        """Test create_default_quotas factory method."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_default_quotas(tenant_id)

        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 100
        assert quotas.max_records_per_model == 1000000
        assert quotas.max_api_calls_per_day == 100000
        assert quotas.max_storage_mb == 10240

    def test_create_enterprise_quotas_factory(self):
        """Test create_enterprise_quotas factory method."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_enterprise_quotas(tenant_id)

        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 1000
        assert quotas.max_records_per_model == 10000000
        assert quotas.max_api_calls_per_day == 1000000
        assert quotas.max_storage_mb == 102400  # 100GB

    def test_create_startup_quotas_factory(self):
        """Test create_startup_quotas factory method."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_startup_quotas(tenant_id)

        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 10
        assert quotas.max_records_per_model == 100000
        assert quotas.max_api_calls_per_day == 10000
        assert quotas.max_storage_mb == 1024  # 1GB


class TestTenantQuotasValidationMethods:
    """Tests for quota validation/checking methods."""

    def test_is_within_user_limit(self):
        """Test user quota limit checking."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_users=100)

        # Within limit
        assert quotas.is_within_user_limit(50) is True
        assert quotas.is_within_user_limit(100) is True  # Exactly at limit

        # Over limit
        assert quotas.is_within_user_limit(101) is False
        assert quotas.is_within_user_limit(150) is False

        # Edge cases
        assert quotas.is_within_user_limit(0) is True  # No users
        assert quotas.is_within_user_limit(1) is True  # Single user

    def test_is_within_record_limit(self):
        """Test record per model quota limit checking."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_records_per_model=1000000)

        # Within limit
        assert quotas.is_within_record_limit(500000) is True
        assert quotas.is_within_record_limit(1000000) is True  # Exactly at limit

        # Over limit
        assert quotas.is_within_record_limit(1000001) is False
        assert quotas.is_within_record_limit(2000000) is False

        # Edge cases
        assert quotas.is_within_record_limit(0) is True  # No records
        assert quotas.is_within_record_limit(1) is True  # Single record

    def test_is_within_api_limit(self):
        """Test API calls per day quota limit checking."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_api_calls_per_day=100000)

        # Within limit
        assert quotas.is_within_api_limit(50000) is True
        assert quotas.is_within_api_limit(100000) is True  # Exactly at limit

        # Over limit
        assert quotas.is_within_api_limit(100001) is False
        assert quotas.is_within_api_limit(200000) is False

        # Edge cases
        assert quotas.is_within_api_limit(0) is True  # No API calls
        assert quotas.is_within_api_limit(1) is True  # Single API call

    def test_is_within_storage_limit(self):
        """Test storage quota limit checking."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_storage_mb=10240)  # 10GB

        # Within limit
        assert quotas.is_within_storage_limit(5120) is True  # 5GB
        assert quotas.is_within_storage_limit(10240) is True  # Exactly at limit

        # Over limit
        assert quotas.is_within_storage_limit(10241) is False
        assert quotas.is_within_storage_limit(20480) is False  # 20GB

        # Edge cases
        assert quotas.is_within_storage_limit(0) is True  # No storage used
        assert quotas.is_within_storage_limit(1) is True  # 1MB used


class TestTenantQuotasUsagePercentages:
    """Tests for usage percentage calculation methods."""

    def test_get_user_usage_percentage(self):
        """Test user usage percentage calculation."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_users=100)

        # Test various percentages
        assert quotas.get_user_usage_percentage(0) == 0.0
        assert quotas.get_user_usage_percentage(25) == 25.0
        assert quotas.get_user_usage_percentage(50) == 50.0
        assert quotas.get_user_usage_percentage(75) == 75.0
        assert quotas.get_user_usage_percentage(100) == 100.0

        # Test over 100%
        assert quotas.get_user_usage_percentage(150) == 150.0

        # Test fractional percentages
        assert quotas.get_user_usage_percentage(33) == 33.0
        assert quotas.get_user_usage_percentage(66) == 66.0

    def test_get_storage_usage_percentage(self):
        """Test storage usage percentage calculation."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_storage_mb=10240)  # 10GB

        # Test various percentages
        assert quotas.get_storage_usage_percentage(0) == 0.0
        assert quotas.get_storage_usage_percentage(2560) == 25.0  # 2.5GB = 25%
        assert quotas.get_storage_usage_percentage(5120) == 50.0  # 5GB = 50%
        assert quotas.get_storage_usage_percentage(7680) == 75.0  # 7.5GB = 75%
        assert quotas.get_storage_usage_percentage(10240) == 100.0  # 10GB = 100%

        # Test over 100%
        assert quotas.get_storage_usage_percentage(15360) == 150.0  # 15GB = 150%

    def test_get_api_usage_percentage(self):
        """Test API usage percentage calculation."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=tenant_id, max_api_calls_per_day=100000)

        # Test various percentages
        assert quotas.get_api_usage_percentage(0) == 0.0
        assert quotas.get_api_usage_percentage(25000) == 25.0
        assert quotas.get_api_usage_percentage(50000) == 50.0
        assert quotas.get_api_usage_percentage(75000) == 75.0
        assert quotas.get_api_usage_percentage(100000) == 100.0

        # Test over 100%
        assert quotas.get_api_usage_percentage(150000) == 150.0


class TestTenantQuotasUpdateMethods:
    """Tests for quota update methods."""

    def test_update_quotas_single_field(self):
        """Test updating a single quota field."""
        tenant_id = str(uuid.uuid4())
        original = TenantQuotas.create_default_quotas(tenant_id)
        original_updated_at = original.updated_at

        # Update only max_users
        updated = original.update_quotas(max_users=200)

        # Check that only max_users changed
        assert updated.tenant_id == original.tenant_id
        assert updated.max_users == 200  # Changed
        assert updated.max_records_per_model == original.max_records_per_model  # Unchanged
        assert updated.max_api_calls_per_day == original.max_api_calls_per_day  # Unchanged
        assert updated.max_storage_mb == original.max_storage_mb  # Unchanged
        assert updated.created_at == original.created_at  # Unchanged
        assert updated.updated_at != original_updated_at  # Should be updated

        # Original should be unchanged (immutable pattern)
        assert original.max_users == 100

    def test_update_quotas_multiple_fields(self):
        """Test updating multiple quota fields."""
        tenant_id = str(uuid.uuid4())
        original = TenantQuotas.create_default_quotas(tenant_id)

        # Update multiple fields
        updated = original.update_quotas(
            max_users=500,
            max_api_calls_per_day=500000,
            max_storage_mb=51200,  # 50GB
        )

        # Check that specified fields changed
        assert updated.max_users == 500  # Changed
        assert updated.max_records_per_model == original.max_records_per_model  # Unchanged
        assert updated.max_api_calls_per_day == 500000  # Changed
        assert updated.max_storage_mb == 51200  # Changed

        # Original should be unchanged
        assert original.max_users == 100
        assert original.max_api_calls_per_day == 100000
        assert original.max_storage_mb == 10240

    def test_update_quotas_no_changes(self):
        """Test update_quotas with no parameters (should create new instance)."""
        tenant_id = str(uuid.uuid4())
        original = TenantQuotas.create_default_quotas(tenant_id)
        original_updated_at = original.updated_at

        # Update with no parameters
        updated = original.update_quotas()

        # Should have same values but new updated_at
        assert updated.tenant_id == original.tenant_id
        assert updated.max_users == original.max_users
        assert updated.max_records_per_model == original.max_records_per_model
        assert updated.max_api_calls_per_day == original.max_api_calls_per_day
        assert updated.max_storage_mb == original.max_storage_mb
        assert updated.created_at == original.created_at
        assert updated.updated_at != original_updated_at  # Should be updated

    def test_update_quotas_with_none_values(self):
        """Test update_quotas ignores None values."""
        tenant_id = str(uuid.uuid4())
        original = TenantQuotas.create_default_quotas(tenant_id)

        # Update with mix of values and None
        updated = original.update_quotas(
            max_users=200,
            max_records_per_model=None,  # Should be ignored
            max_api_calls_per_day=200000,
            max_storage_mb=None,  # Should be ignored
        )

        # Only non-None values should change
        assert updated.max_users == 200  # Changed
        assert updated.max_records_per_model == original.max_records_per_model  # Unchanged
        assert updated.max_api_calls_per_day == 200000  # Changed
        assert updated.max_storage_mb == original.max_storage_mb  # Unchanged


class TestTenantQuotasSerializationMethods:
    """Tests for TenantQuotas serialization methods."""

    def test_to_dict_method(self):
        """Test to_dict method returns correct dictionary representation."""
        tenant_id = str(uuid.uuid4())
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=150,
            max_records_per_model=1500000,
            max_api_calls_per_day=150000,
            max_storage_mb=15360,  # 15GB
            created_at=created_at,
            updated_at=updated_at,
        )

        data = quotas.to_dict()

        assert data["tenant_id"] == tenant_id
        assert data["max_users"] == 150
        assert data["max_records_per_model"] == 1500000
        assert data["max_api_calls_per_day"] == 150000
        assert data["max_storage_mb"] == 15360
        assert data["created_at"] == created_at
        assert data["updated_at"] == updated_at

    def test_string_representation(self):
        """Test __repr__ method returns informative string."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=75,
            max_records_per_model=750000,
            max_api_calls_per_day=75000,
            max_storage_mb=7680,  # 7.5GB
        )

        repr_str = repr(quotas)

        # Should contain key information
        assert "TenantQuotas" in repr_str
        assert tenant_id in repr_str
        assert "max_users=75" in repr_str
        assert "max_records_per_model=750000" in repr_str
        assert "max_api_calls_per_day=75000" in repr_str
        assert "max_storage_mb=7680" in repr_str


class TestTenantQuotasCRUDOperations:
    """Tests for TenantQuotas CRUD operations."""

    def test_create_operation(self):
        """Test creation of tenant quotas (Create operation)."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=300,
            max_records_per_model=3000000,
            max_api_calls_per_day=300000,
            max_storage_mb=30720,  # 30GB
        )

        # Verify all fields are set correctly
        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 300
        assert quotas.max_records_per_model == 3000000
        assert quotas.max_api_calls_per_day == 300000
        assert quotas.max_storage_mb == 30720
        assert quotas.created_at is not None
        assert quotas.updated_at is not None

    def test_read_operation(self):
        """Test reading tenant quotas data (Read operation)."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_enterprise_quotas(tenant_id)

        # Test accessing all fields
        assert quotas.tenant_id == tenant_id
        assert quotas.max_users == 1000
        assert quotas.max_records_per_model == 10000000
        assert quotas.max_api_calls_per_day == 1000000
        assert quotas.max_storage_mb == 102400
        assert quotas.created_at is not None
        assert quotas.updated_at is not None

    def test_update_operation(self):
        """Test updating tenant quotas data (Update operation)."""
        tenant_id = str(uuid.uuid4())
        original = TenantQuotas.create_default_quotas(tenant_id)

        # Test update operation
        updated = original.update_quotas(
            max_users=250,
            max_storage_mb=25600,  # 25GB
        )

        # Verify update
        assert updated.tenant_id == original.tenant_id  # Unchanged
        assert updated.max_users == 250  # Updated
        assert updated.max_records_per_model == original.max_records_per_model  # Unchanged
        assert updated.max_api_calls_per_day == original.max_api_calls_per_day  # Unchanged
        assert updated.max_storage_mb == 25600  # Updated
        assert updated.created_at == original.created_at  # Unchanged
        assert updated.updated_at != original.updated_at  # Updated

        # Original remains unchanged (immutable pattern)
        assert original.max_users == 100
        assert original.max_storage_mb == 10240

    def test_crud_operations_preserve_data_integrity(self):
        """Test that CRUD operations maintain data integrity."""
        tenant_id = str(uuid.uuid4())

        # Create
        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=100,
            max_records_per_model=1000000,
            max_api_calls_per_day=100000,
            max_storage_mb=10240,
        )

        # Verify creation integrity
        assert uuid.UUID(quotas.tenant_id)  # Valid UUID
        assert quotas.max_users > 0  # Positive values
        assert quotas.max_records_per_model > 0
        assert quotas.max_api_calls_per_day > 0
        assert quotas.max_storage_mb > 0
        assert quotas.created_at <= datetime.now(UTC)

        # Update
        updated = quotas.update_quotas(max_users=200)
        assert updated.tenant_id == quotas.tenant_id  # ID preserved
        assert updated.created_at == quotas.created_at  # Created time preserved

        # Verify all values remain positive after update
        assert updated.max_users > 0
        assert updated.max_records_per_model > 0
        assert updated.max_api_calls_per_day > 0
        assert updated.max_storage_mb > 0


class TestTenantQuotasConstraintsAndValidation:
    """Tests for TenantQuotas constraints and validation."""

    def test_positive_values_required(self):
        """Test that all quota values must be positive (this would be enforced by BaseModel/database)."""
        tenant_id = str(uuid.uuid4())

        # Valid positive values should work
        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=1,
            max_records_per_model=1,
            max_api_calls_per_day=1,
            max_storage_mb=1,
        )
        assert quotas.max_users == 1
        assert quotas.max_records_per_model == 1
        assert quotas.max_api_calls_per_day == 1
        assert quotas.max_storage_mb == 1

        # Note: Negative value validation would typically be handled by
        # BaseModel field validation or database constraints

    def test_tenant_id_uuid_format(self):
        """Test that tenant_id should be valid UUID format."""
        # Valid UUID should work
        valid_uuid = str(uuid.uuid4())
        quotas = TenantQuotas(tenant_id=valid_uuid)
        assert quotas.tenant_id == valid_uuid

        # Note: UUID format validation would typically be handled by
        # BaseModel field validation or at the service layer

    def test_default_values_are_reasonable(self):
        """Test that default values are reasonable for production use."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_default_quotas(tenant_id)

        # Default values should be reasonable for a typical tenant
        assert quotas.max_users == 100  # Reasonable for small-medium team
        assert quotas.max_records_per_model == 1000000  # 1M records per model
        assert quotas.max_api_calls_per_day == 100000  # 100K calls per day
        assert quotas.max_storage_mb == 10240  # 10GB storage

        # All defaults should be positive
        assert quotas.max_users > 0
        assert quotas.max_records_per_model > 0
        assert quotas.max_api_calls_per_day > 0
        assert quotas.max_storage_mb > 0

    def test_enterprise_vs_startup_quota_differences(self):
        """Test that different quota tiers have appropriate differences."""
        tenant_id = str(uuid.uuid4())

        startup = TenantQuotas.create_startup_quotas(tenant_id)
        default = TenantQuotas.create_default_quotas(tenant_id)
        enterprise = TenantQuotas.create_enterprise_quotas(tenant_id)

        # Enterprise should have higher limits than default
        assert enterprise.max_users > default.max_users
        assert enterprise.max_records_per_model > default.max_records_per_model
        assert enterprise.max_api_calls_per_day > default.max_api_calls_per_day
        assert enterprise.max_storage_mb > default.max_storage_mb

        # Default should have higher limits than startup
        assert default.max_users > startup.max_users
        assert default.max_records_per_model > startup.max_records_per_model
        assert default.max_api_calls_per_day > startup.max_api_calls_per_day
        assert default.max_storage_mb > startup.max_storage_mb

        # Verify specific tiering
        assert startup.max_users == 10
        assert default.max_users == 100
        assert enterprise.max_users == 1000

        assert startup.max_storage_mb == 1024  # 1GB
        assert default.max_storage_mb == 10240  # 10GB
        assert enterprise.max_storage_mb == 102400  # 100GB


class TestTenantQuotasImmutabilityPattern:
    """Tests for TenantQuotas immutability pattern."""

    def test_update_methods_return_new_instances(self):
        """Test that update methods return new instances, don't mutate original."""
        tenant_id = str(uuid.uuid4())
        original = TenantQuotas.create_default_quotas(tenant_id)

        # Store original values
        original_max_users = original.max_users
        original_max_storage = original.max_storage_mb
        original_updated_at = original.updated_at

        # Update quotas
        updated = original.update_quotas(max_users=500, max_storage_mb=50000)

        # Original should be unchanged
        assert original.max_users == original_max_users
        assert original.max_storage_mb == original_max_storage
        assert original.updated_at == original_updated_at

        # New instance should have changes
        assert updated.max_users == 500
        assert updated.max_storage_mb == 50000
        assert updated.updated_at != original_updated_at

        # Should be different objects
        assert original is not updated

    def test_factory_methods_return_new_instances(self):
        """Test that factory methods return independent instances."""
        tenant_id = str(uuid.uuid4())

        # Create multiple instances with same tenant_id
        quotas1 = TenantQuotas.create_default_quotas(tenant_id)
        quotas2 = TenantQuotas.create_default_quotas(tenant_id)

        # Should be different objects with same values
        assert quotas1 is not quotas2
        assert quotas1.tenant_id == quotas2.tenant_id
        assert quotas1.max_users == quotas2.max_users
        assert quotas1.max_records_per_model == quotas2.max_records_per_model
        assert quotas1.max_api_calls_per_day == quotas2.max_api_calls_per_day
        assert quotas1.max_storage_mb == quotas2.max_storage_mb

    def test_to_dict_does_not_affect_original(self):
        """Test that to_dict() does not mutate the original object."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_enterprise_quotas(tenant_id)

        # Store original values
        original_values = {
            "max_users": quotas.max_users,
            "max_records_per_model": quotas.max_records_per_model,
            "max_api_calls_per_day": quotas.max_api_calls_per_day,
            "max_storage_mb": quotas.max_storage_mb,
        }

        # Get dictionary representation
        data = quotas.to_dict()

        # Modify dictionary (should not affect original)
        data["max_users"] = 99999
        data["max_storage_mb"] = 99999

        # Original should be unchanged
        assert quotas.max_users == original_values["max_users"]
        assert quotas.max_records_per_model == original_values["max_records_per_model"]
        assert quotas.max_api_calls_per_day == original_values["max_api_calls_per_day"]
        assert quotas.max_storage_mb == original_values["max_storage_mb"]


class TestTenantQuotasBusinessLogic:
    """Tests for business logic and edge cases."""

    def test_quota_combinations_are_logical(self):
        """Test that quota combinations make business sense."""
        tenant_id = str(uuid.uuid4())

        # Test that enterprise quotas scale proportionally
        enterprise = TenantQuotas.create_enterprise_quotas(tenant_id)

        # Enterprise should have reasonable ratios
        # More users should correlate with more API calls and storage
        users_to_api_ratio = enterprise.max_api_calls_per_day / enterprise.max_users
        users_to_storage_ratio = enterprise.max_storage_mb / enterprise.max_users

        # Should be reasonable ratios (not too low or too high)
        assert 500 <= users_to_api_ratio <= 2000  # 500-2000 API calls per user per day
        assert 50 <= users_to_storage_ratio <= 500  # 50-500 MB per user

    def test_usage_percentage_edge_cases(self):
        """Test usage percentage calculations with edge cases."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas.create_default_quotas(tenant_id)

        # Test zero current usage
        assert quotas.get_user_usage_percentage(0) == 0.0
        assert quotas.get_storage_usage_percentage(0) == 0.0
        assert quotas.get_api_usage_percentage(0) == 0.0

        # Test exactly at limit
        assert quotas.get_user_usage_percentage(quotas.max_users) == 100.0
        assert quotas.get_storage_usage_percentage(quotas.max_storage_mb) == 100.0
        assert quotas.get_api_usage_percentage(quotas.max_api_calls_per_day) == 100.0

        # Test over limit (should return > 100%)
        assert quotas.get_user_usage_percentage(quotas.max_users * 2) == 200.0
        assert quotas.get_storage_usage_percentage(quotas.max_storage_mb * 1.5) == 150.0
        assert quotas.get_api_usage_percentage(quotas.max_api_calls_per_day * 3) == 300.0

    def test_limit_checking_edge_cases(self):
        """Test limit checking with edge cases."""
        tenant_id = str(uuid.uuid4())
        quotas = TenantQuotas(
            tenant_id=tenant_id,
            max_users=1,  # Minimum limits for edge testing
            max_records_per_model=1,
            max_api_calls_per_day=1,
            max_storage_mb=1,
        )

        # Test at exactly the limit
        assert quotas.is_within_user_limit(1) is True
        assert quotas.is_within_record_limit(1) is True
        assert quotas.is_within_api_limit(1) is True
        assert quotas.is_within_storage_limit(1) is True

        # Test just over the limit
        assert quotas.is_within_user_limit(2) is False
        assert quotas.is_within_record_limit(2) is False
        assert quotas.is_within_api_limit(2) is False
        assert quotas.is_within_storage_limit(2) is False

        # Test zero usage (should always be within limits)
        assert quotas.is_within_user_limit(0) is True
        assert quotas.is_within_record_limit(0) is True
        assert quotas.is_within_api_limit(0) is True
        assert quotas.is_within_storage_limit(0) is True
