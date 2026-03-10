"""Tests for TenantPricingConfig model - Database Schema Design.

These tests define the expected behavior of the TenantPricingConfig model for
multi-tenant pricing configuration as required by Task 1.1.
"""
import pytest
import uuid
import datetime
from unittest.mock import MagicMock

from registry.models.tenant_pricing_config import TenantPricingConfig


class TestTenantPricingConfig:
    """Tests for TenantPricingConfig model."""

    def test_create_minimal_config(self):
        """Create config with required fields only."""
        tenant_id = str(uuid.uuid4())
        config = TenantPricingConfig(
            tenant_id=tenant_id
        )

        assert str(config.tenant_id) == tenant_id
        assert config.default_pricer_id is None
        assert config.fallback_pricer_id is None
        assert config.config_json == {}

        # Should have auto-generated timestamps
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_create_full_config(self):
        """Create config with all fields."""
        tenant_id = str(uuid.uuid4())
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)

        config_json = {
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
            "features": ["batch_pricing", "dual_pricing"],
            "max_batch_size": 10000,
            "custom_curves_allowed": True
        }

        config = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json=config_json,
            created_at=created_at,
            updated_at=updated_at
        )

        assert str(config.tenant_id) == tenant_id
        assert config.default_pricer_id == "quantlib-v1.18"
        assert config.fallback_pricer_id == "treasury-v2.3"
        assert config.config_json == config_json
        assert config.created_at == created_at
        assert config.updated_at == updated_at

    def test_create_system_tenant_config(self):
        """Create system tenant config using factory method."""
        system_config = TenantPricingConfig.create_system_tenant_config()

        assert str(system_config.tenant_id) == "00000000-0000-0000-0000-000000000000"
        assert system_config.default_pricer_id == "quantlib-v1.18"
        assert system_config.fallback_pricer_id == "treasury-v2.3"

        # Check system tenant has full access
        assert "quantlib-v1.18" in system_config.get_allowed_pricers()
        assert "treasury-v2.3" in system_config.get_allowed_pricers()
        assert "batch_pricing" in system_config.get_enabled_features()
        assert "dual_pricing" in system_config.get_enabled_features()
        assert "monte_carlo" in system_config.get_enabled_features()
        assert system_config.get_max_batch_size() == 50000
        assert system_config.allows_custom_curves() is True
        assert system_config.allows_advanced_models() is True

    def test_create_default_tenant_config(self):
        """Create default tenant config using factory method."""
        tenant_id = str(uuid.uuid4())
        default_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        assert str(default_config.tenant_id) == tenant_id
        assert default_config.default_pricer_id == "quantlib-v1.18"
        assert default_config.fallback_pricer_id == "treasury-v2.3"

        # Check default tenant has limited access
        assert default_config.get_allowed_pricers() == ["quantlib-v1.18"]
        assert default_config.get_enabled_features() == ["batch_pricing"]
        assert default_config.get_max_batch_size() == 1000
        assert default_config.allows_custom_curves() is False
        assert default_config.allows_advanced_models() is False

    def test_get_allowed_pricers(self):
        """Test getting allowed pricers list."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3", "custom-v1.0"]
            }
        )

        allowed = config.get_allowed_pricers()
        assert allowed == ["quantlib-v1.18", "treasury-v2.3", "custom-v1.0"]

        # Test with no config
        empty_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert empty_config.get_allowed_pricers() == []

        # Test with empty allowed_pricers
        empty_pricers = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"allowed_pricers": []}
        )
        assert empty_pricers.get_allowed_pricers() == []

    def test_get_enabled_features(self):
        """Test getting enabled features list."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={
                "features": ["batch_pricing", "dual_pricing", "monte_carlo"]
            }
        )

        features = config.get_enabled_features()
        assert features == ["batch_pricing", "dual_pricing", "monte_carlo"]

        # Test with no config
        empty_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert empty_config.get_enabled_features() == []

    def test_get_max_batch_size(self):
        """Test getting max batch size."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"max_batch_size": 5000}
        )

        assert config.get_max_batch_size() == 5000

        # Test with no config (default)
        empty_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert empty_config.get_max_batch_size() == 100

        # Test with no max_batch_size in config
        no_batch_config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"features": ["batch_pricing"]}
        )
        assert no_batch_config.get_max_batch_size() == 100

    def test_is_pricer_allowed(self):
        """Test checking if pricer is allowed."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"]
            }
        )

        assert config.is_pricer_allowed("quantlib-v1.18") is True
        assert config.is_pricer_allowed("treasury-v2.3") is True
        assert config.is_pricer_allowed("custom-v1.0") is False
        assert config.is_pricer_allowed("nonexistent") is False

        # Test with empty allowed list
        empty_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert empty_config.is_pricer_allowed("quantlib-v1.18") is False

    def test_is_feature_enabled(self):
        """Test checking if feature is enabled."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={
                "features": ["batch_pricing", "dual_pricing"]
            }
        )

        assert config.is_feature_enabled("batch_pricing") is True
        assert config.is_feature_enabled("dual_pricing") is True
        assert config.is_feature_enabled("monte_carlo") is False
        assert config.is_feature_enabled("nonexistent") is False

        # Test with empty features list
        empty_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert empty_config.is_feature_enabled("batch_pricing") is False

    def test_allows_custom_curves(self):
        """Test checking if custom curves are allowed."""
        allowed_config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"custom_curves_allowed": True}
        )
        assert allowed_config.allows_custom_curves() is True

        not_allowed_config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"custom_curves_allowed": False}
        )
        assert not_allowed_config.allows_custom_curves() is False

        # Test default (should be False)
        default_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert default_config.allows_custom_curves() is False

    def test_allows_advanced_models(self):
        """Test checking if advanced models are allowed."""
        allowed_config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"advanced_models_allowed": True}
        )
        assert allowed_config.allows_advanced_models() is True

        not_allowed_config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"advanced_models_allowed": False}
        )
        assert not_allowed_config.allows_advanced_models() is False

        # Test default (should be False)
        default_config = TenantPricingConfig(tenant_id=str(uuid.uuid4()))
        assert default_config.allows_advanced_models() is False

    def test_update_configuration(self):
        """Test updating configuration."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={
                "allowed_pricers": ["quantlib-v1.18"],
                "max_batch_size": 1000
            }
        )

        original_updated_at = config.updated_at
        updated_config = config.update_configuration({
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
            "features": ["batch_pricing", "dual_pricing"],
            "custom_curves_allowed": True
        })

        # Check merged configuration
        expected_config = {
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
            "max_batch_size": 1000,  # Preserved from original
            "features": ["batch_pricing", "dual_pricing"],  # New
            "custom_curves_allowed": True  # New
        }
        assert updated_config.config_json == expected_config
        assert updated_config.updated_at.timestamp() > original_updated_at.timestamp()

        # Original unchanged
        assert config.config_json == {
            "allowed_pricers": ["quantlib-v1.18"],
            "max_batch_size": 1000
        }

    def test_set_default_pricer(self):
        """Test setting default pricer."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            config_json={"allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"]}
        )

        updated_config = config.set_default_pricer("treasury-v2.3")

        assert updated_config.default_pricer_id == "treasury-v2.3"
        assert updated_config.updated_at.timestamp() > config.updated_at.timestamp()

        # Original unchanged
        assert config.default_pricer_id == "quantlib-v1.18"

    def test_set_default_pricer_not_allowed(self):
        """Test setting default pricer to non-allowed pricer fails."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"allowed_pricers": ["quantlib-v1.18"]}
        )

        with pytest.raises(ValueError, match="Pricer treasury-v2.3 is not allowed"):
            config.set_default_pricer("treasury-v2.3")

    def test_set_fallback_pricer(self):
        """Test setting fallback pricer."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={"allowed_pricers": ["quantlib-v1.18", "treasury-v2.3", "custom-v1.0"]}
        )

        updated_config = config.set_fallback_pricer("custom-v1.0")

        assert updated_config.fallback_pricer_id == "custom-v1.0"
        assert updated_config.updated_at.timestamp() > config.updated_at.timestamp()

        # Test removing fallback
        no_fallback = config.set_fallback_pricer(None)
        assert no_fallback.fallback_pricer_id is None

    def test_set_fallback_pricer_validation(self):
        """Test fallback pricer validation."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            config_json={"allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"]}
        )

        # Not allowed pricer
        with pytest.raises(ValueError, match="Pricer custom-v1.0 is not allowed"):
            config.set_fallback_pricer("custom-v1.0")

        # Same as default pricer
        with pytest.raises(ValueError, match="Fallback pricer cannot be the same as default"):
            config.set_fallback_pricer("quantlib-v1.18")

    def test_enable_feature(self):
        """Test enabling features."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"features": ["batch_pricing"]}
        )

        updated_config = config.enable_feature("dual_pricing")

        assert "batch_pricing" in updated_config.get_enabled_features()
        assert "dual_pricing" in updated_config.get_enabled_features()

        # Enabling already enabled feature should be idempotent
        same_config = updated_config.enable_feature("batch_pricing")
        features = same_config.get_enabled_features()
        assert features.count("batch_pricing") == 1  # Should not duplicate

    def test_disable_feature(self):
        """Test disabling features."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"features": ["batch_pricing", "dual_pricing", "monte_carlo"]}
        )

        updated_config = config.disable_feature("dual_pricing")

        features = updated_config.get_enabled_features()
        assert "batch_pricing" in features
        assert "dual_pricing" not in features
        assert "monte_carlo" in features

        # Disabling non-existent feature should be safe
        same_config = updated_config.disable_feature("nonexistent")
        assert same_config.get_enabled_features() == features

    def test_add_allowed_pricer(self):
        """Test adding allowed pricer."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={"allowed_pricers": ["quantlib-v1.18"]}
        )

        updated_config = config.add_allowed_pricer("treasury-v2.3")

        allowed = updated_config.get_allowed_pricers()
        assert "quantlib-v1.18" in allowed
        assert "treasury-v2.3" in allowed

        # Adding already allowed pricer should be idempotent
        same_config = updated_config.add_allowed_pricer("quantlib-v1.18")
        allowed_again = same_config.get_allowed_pricers()
        assert allowed_again.count("quantlib-v1.18") == 1  # Should not duplicate

    def test_remove_allowed_pricer(self):
        """Test removing allowed pricer."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={"allowed_pricers": ["quantlib-v1.18", "treasury-v2.3", "custom-v1.0"]}
        )

        updated_config = config.remove_allowed_pricer("custom-v1.0")

        allowed = updated_config.get_allowed_pricers()
        assert "quantlib-v1.18" in allowed
        assert "treasury-v2.3" in allowed
        assert "custom-v1.0" not in allowed

        # Removing non-existent pricer should be safe
        same_config = updated_config.remove_allowed_pricer("nonexistent")
        assert same_config.get_allowed_pricers() == allowed

    def test_remove_allowed_pricer_validation(self):
        """Test removing allowed pricer validation."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={"allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"]}
        )

        # Cannot remove default pricer
        with pytest.raises(ValueError, match="Cannot remove default pricer"):
            config.remove_allowed_pricer("quantlib-v1.18")

        # Cannot remove fallback pricer
        with pytest.raises(ValueError, match="Cannot remove fallback pricer"):
            config.remove_allowed_pricer("treasury-v2.3")

    def test_serialization_to_dict(self):
        """Config serializes to dictionary with ISO timestamps."""
        tenant_id = str(uuid.uuid4())
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)

        config = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={"features": ["batch_pricing"]},
            created_at=created_at,
            updated_at=updated_at
        )

        data = config.to_dict()

        assert data["tenant_id"] == tenant_id  # Should be string
        assert data["default_pricer_id"] == "quantlib-v1.18"
        assert data["fallback_pricer_id"] == "treasury-v2.3"
        assert data["config_json"] == {"features": ["batch_pricing"]}
        assert data["created_at"] == created_at.isoformat()
        assert data["updated_at"] == updated_at.isoformat()

    def test_immutability_through_methods(self):
        """Config methods return new instances, don't mutate original."""
        original = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
                "features": ["batch_pricing"]
            }
        )

        # Test all mutation methods
        updated_config = original.update_configuration({"new_key": "new_value"})
        new_default = original.set_default_pricer("treasury-v2.3")
        enabled_feature = original.enable_feature("dual_pricing")
        added_pricer = original.add_allowed_pricer("custom-v1.0")

        # Original should be unchanged
        assert original.config_json == {
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
            "features": ["batch_pricing"]
        }
        assert original.default_pricer_id == "quantlib-v1.18"

        # New instances should be different
        assert "new_key" in updated_config.config_json
        assert new_default.default_pricer_id == "treasury-v2.3"
        assert "dual_pricing" in enabled_feature.get_enabled_features()
        assert "custom-v1.0" in added_pricer.get_allowed_pricers()

    def test_string_representation(self):
        """Test string representation methods."""
        tenant_id = str(uuid.uuid4())
        config = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3"
        )

        str_repr = str(config)
        assert "TenantPricingConfig(" in str_repr
        assert tenant_id in str_repr
        assert "quantlib-v1.18" in str_repr
        assert "treasury-v2.3" in str_repr

        repr_str = repr(config)
        assert "TenantPricingConfig(" in repr_str
        assert f"tenant_id='{tenant_id}'" in repr_str


class TestTenantPricingConfigConstraints:
    """Tests for TenantPricingConfig database constraints."""

    def test_different_pricers_constraint_logic(self):
        """Test different pricers constraint validation logic."""
        tenant_id = str(uuid.uuid4())

        # Valid: different pricers
        config1 = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3"
        )
        # Constraint: default_pricer_id != fallback_pricer_id OR fallback_pricer_id IS NULL
        constraint_passes = (
            config1.default_pricer_id != config1.fallback_pricer_id or
            config1.fallback_pricer_id is None
        )
        assert constraint_passes is True

        # Valid: no fallback pricer
        config2 = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id=None
        )
        constraint_passes = (
            config2.default_pricer_id != config2.fallback_pricer_id or
            config2.fallback_pricer_id is None
        )
        assert constraint_passes is True

        # Invalid: same pricer for both
        config3 = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="quantlib-v1.18"
        )
        constraint_passes = (
            config3.default_pricer_id != config3.fallback_pricer_id or
            config3.fallback_pricer_id is None
        )
        assert constraint_passes is False


class TestTenantPricingConfigBusinessLogic:
    """Tests for TenantPricingConfig business logic."""

    def test_tenant_isolation(self):
        """Test tenant isolation in pricing configuration."""
        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        # Different tenants should have independent configurations
        tenant1_config = TenantPricingConfig(
            tenant_id=tenant1_id,
            default_pricer_id="quantlib-v1.18",
            config_json={"allowed_pricers": ["quantlib-v1.18"]}
        )

        tenant2_config = TenantPricingConfig(
            tenant_id=tenant2_id,
            default_pricer_id="treasury-v2.3",
            config_json={"allowed_pricers": ["treasury-v2.3"]}
        )

        # Configurations should be independent
        assert tenant1_config.is_pricer_allowed("quantlib-v1.18") is True
        assert tenant1_config.is_pricer_allowed("treasury-v2.3") is False

        assert tenant2_config.is_pricer_allowed("treasury-v2.3") is True
        assert tenant2_config.is_pricer_allowed("quantlib-v1.18") is False

    def test_feature_access_control(self):
        """Test feature-based access control."""
        # Basic tenant
        basic_config = TenantPricingConfig.create_default_tenant_config(str(uuid.uuid4()))

        # Premium tenant
        premium_config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json={
                "features": ["batch_pricing", "dual_pricing", "monte_carlo", "custom_models"],
                "max_batch_size": 10000
            }
        )

        # Basic tenant has limited access
        assert basic_config.is_feature_enabled("batch_pricing") is True
        assert basic_config.is_feature_enabled("dual_pricing") is False
        assert basic_config.is_feature_enabled("monte_carlo") is False
        assert basic_config.get_max_batch_size() == 1000

        # Premium tenant has extended access
        assert premium_config.is_feature_enabled("batch_pricing") is True
        assert premium_config.is_feature_enabled("dual_pricing") is True
        assert premium_config.is_feature_enabled("monte_carlo") is True
        assert premium_config.get_max_batch_size() == 10000

    def test_pricer_preference_hierarchy(self):
        """Test pricer preference and fallback hierarchy."""
        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3", "custom-v1.0"]
            }
        )

        # Primary preference
        assert config.default_pricer_id == "quantlib-v1.18"

        # Fallback preference
        assert config.fallback_pricer_id == "treasury-v2.3"

        # All allowed pricers
        allowed = config.get_allowed_pricers()
        assert "quantlib-v1.18" in allowed
        assert "treasury-v2.3" in allowed
        assert "custom-v1.0" in allowed

    def test_configuration_evolution(self):
        """Test configuration changes over time."""
        initial_config = TenantPricingConfig.create_default_tenant_config(str(uuid.uuid4()))

        # Start with basic configuration
        assert initial_config.get_allowed_pricers() == ["quantlib-v1.18"]
        assert initial_config.get_max_batch_size() == 1000

        # Upgrade to premium features
        upgraded_config = initial_config.update_configuration({
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
            "features": ["batch_pricing", "dual_pricing", "monte_carlo"],
            "max_batch_size": 10000,
            "custom_curves_allowed": True,
            "advanced_models_allowed": True
        })

        # Verify upgrade
        assert len(upgraded_config.get_allowed_pricers()) == 2
        assert upgraded_config.is_feature_enabled("dual_pricing") is True
        assert upgraded_config.get_max_batch_size() == 10000
        assert upgraded_config.allows_custom_curves() is True

        # Add more pricers
        expanded_config = upgraded_config.add_allowed_pricer("custom-v1.0")
        assert "custom-v1.0" in expanded_config.get_allowed_pricers()

        # Enable additional features
        feature_rich_config = expanded_config.enable_feature("real_time_pricing")
        assert feature_rich_config.is_feature_enabled("real_time_pricing") is True

    def test_system_vs_regular_tenant_differences(self):
        """Test differences between system and regular tenant configurations."""
        system_config = TenantPricingConfig.create_system_tenant_config()
        regular_config = TenantPricingConfig.create_default_tenant_config(str(uuid.uuid4()))

        # System tenant has more access
        assert len(system_config.get_allowed_pricers()) > len(regular_config.get_allowed_pricers())
        assert len(system_config.get_enabled_features()) > len(regular_config.get_enabled_features())
        assert system_config.get_max_batch_size() > regular_config.get_max_batch_size()
        assert system_config.allows_custom_curves() != regular_config.allows_custom_curves()
        assert system_config.allows_advanced_models() != regular_config.allows_advanced_models()

        # Regular tenant is more restricted
        assert "dual_pricing" not in regular_config.get_enabled_features()
        assert "monte_carlo" not in regular_config.get_enabled_features()
        assert regular_config.allows_custom_curves() is False
        assert regular_config.allows_advanced_models() is False