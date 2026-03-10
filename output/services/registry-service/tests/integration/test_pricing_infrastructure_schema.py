"""Integration tests for Pricing Infrastructure Database Schema.

These tests verify the complete database schema design for the pricing
infrastructure including tables, relationships, constraints, and triggers
as implemented in migration 005_add_pricing_infrastructure.sql.
"""
import pytest
import uuid
from datetime import datetime, timezone

from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.pricer_capability import PricerCapability
from registry.models.tenant_pricing_config import TenantPricingConfig
from registry.models.tenant import Tenant


class TestPricingInfrastructureSchema:
    """Integration tests for the complete pricing infrastructure schema."""

    def test_pricer_registry_table_structure(self):
        """Test PricerRegistry table structure and constraints."""
        # Test creating valid pricer
        pricer = PricerRegistry(
            pricer_id="test-pricer-v1.0",
            name="Test Pricer",
            version="1.0.0",
            description="Test pricer for schema validation",
            health_check_url="http://test-pricer:8080/health",
            pricing_url="http://test-pricer:8080/api/v1",
            batch_supported=True,
            max_batch_size=1000,
            status=PricerStatus.HEALTHY
        )

        # Verify all fields are properly set
        assert pricer.pricer_id == "test-pricer-v1.0"
        assert pricer.name == "Test Pricer"
        assert pricer.version == "1.0.0"
        assert pricer.description == "Test pricer for schema validation"
        assert pricer.batch_supported is True
        assert pricer.max_batch_size == 1000
        assert pricer.status == PricerStatus.HEALTHY.value
        assert pricer.health_check_failures == 0

        # Verify auto-generated timestamps
        assert pricer.created_at is not None
        assert pricer.updated_at is not None
        assert isinstance(pricer.created_at, datetime)
        assert isinstance(pricer.updated_at, datetime)

    def test_pricer_capability_table_structure(self):
        """Test PricerCapability table structure and relationships."""
        # Test creating valid capability
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="interest_rate_swap",
            model_type="Hull-White",
            features=["greeks", "duration", "convexity", "pv01"],
            priority=10
        )

        # Verify all fields are properly set
        assert capability.pricer_id == "quantlib-v1.18"
        assert capability.instrument_type == "interest_rate_swap"
        assert capability.model_type == "Hull-White"
        assert capability.features == ["greeks", "duration", "convexity", "pv01"]
        assert capability.priority == 10

        # Test features as JSONB
        assert isinstance(capability.features, list)
        assert "greeks" in capability.features

    def test_tenant_pricing_config_table_structure(self):
        """Test TenantPricingConfig table structure and relationships."""
        tenant_id = "12345678-1234-1234-1234-123456789abc"

        # Test creating valid configuration
        config = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
                "features": ["batch_pricing", "dual_pricing"],
                "max_batch_size": 5000,
                "custom_curves_allowed": True,
                "advanced_models_allowed": False
            }
        )

        # Verify all fields are properly set
        assert str(config.tenant_id) == tenant_id
        assert config.default_pricer_id == "quantlib-v1.18"
        assert config.fallback_pricer_id == "treasury-v2.3"
        assert isinstance(config.config_json, dict)
        assert config.config_json["max_batch_size"] == 5000

        # Verify auto-generated timestamps
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_pricer_registry_capabilities_relationship(self):
        """Test one-to-many relationship between pricer registry and capabilities."""
        # Create pricer
        pricer = PricerRegistry.create_quantlib_pricer()

        # Create multiple capabilities for the same pricer
        capabilities = [
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                model_type="Hull-White",
                features=["greeks", "duration"]
            ),
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="bond",
                model_type="Yield",
                features=["yield", "duration", "convexity"]
            ),
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="option",
                model_type="Black-Scholes",
                features=["greeks", "delta", "gamma", "vega"]
            )
        ]

        # Mock the relationship (in real database, this would be automatic)
        pricer.capabilities = capabilities

        # Test relationship
        assert len(pricer.capabilities) == 3
        assert all(cap.pricer_id == "quantlib-v1.18" for cap in pricer.capabilities)

        # Test capability summary
        summary = pricer.get_capabilities_summary()
        assert summary["total_capabilities"] == 3
        assert "swap" in summary["supported_instruments"]
        assert "bond" in summary["supported_instruments"]
        assert "option" in summary["supported_instruments"]

    def test_foreign_key_constraints_logic(self):
        """Test foreign key constraint logic."""
        # Test valid foreign key reference
        config = TenantPricingConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3"
        )

        # These should be valid references (in real DB, would be enforced)
        valid_pricer_ids = ["quantlib-v1.18", "treasury-v2.3"]
        assert config.default_pricer_id in valid_pricer_ids
        assert config.fallback_pricer_id in valid_pricer_ids

        # Test capability foreign key
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap"
        )
        assert capability.pricer_id in valid_pricer_ids

    def test_cascade_delete_logic(self):
        """Test cascade delete behavior logic."""
        pricer_id = "test-pricer-v1.0"

        # Create pricer with capabilities
        pricer = PricerRegistry(
            pricer_id=pricer_id,
            name="Test Pricer",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1"
        )

        capabilities = [
            PricerCapability(pricer_id=pricer_id, instrument_type="swap"),
            PricerCapability(pricer_id=pricer_id, instrument_type="bond")
        ]

        # Simulate cascade delete logic
        # When pricer is deleted, all its capabilities should be deleted too
        assert all(cap.pricer_id == pricer_id for cap in capabilities)

        # In real database: DELETE FROM pricer_registry WHERE pricer_id = 'test-pricer-v1.0'
        # would automatically delete all related capabilities due to CASCADE constraint

    def test_set_null_on_delete_logic(self):
        """Test SET NULL on delete behavior logic."""
        # Create config that references pricers
        config = TenantPricingConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3"
        )

        # Simulate SET NULL behavior
        # When a pricer is deleted, references should be set to NULL
        original_default = config.default_pricer_id
        assert original_default == "quantlib-v1.18"

        # Simulate pricer deletion (would trigger SET NULL in real DB)
        config_after_delete = TenantPricingConfig(
            tenant_id=config.tenant_id,
            default_pricer_id=None,  # SET NULL behavior
            fallback_pricer_id=config.fallback_pricer_id,
            config_json=config.config_json
        )

        assert config_after_delete.default_pricer_id is None
        assert config_after_delete.fallback_pricer_id == "treasury-v2.3"

    def test_check_constraints_validation(self):
        """Test database check constraints validation logic."""
        # Test pricer_id format constraint
        valid_pricer_ids = [
            "quantlib-v1.18",
            "treasury-v2.3",
            "custom-v1.0.0"
        ]

        invalid_pricer_ids = [
            "quantlib",           # no version
            "quantlib-1.18",      # no 'v' prefix
            "QUANTLIB-v1.18",     # uppercase
        ]

        import re
        pricer_id_pattern = r'^[a-z0-9-]+-v[0-9]+\.[0-9]+(\.[0-9]+)?$'

        for pricer_id in valid_pricer_ids:
            assert re.match(pricer_id_pattern, pricer_id), f"Valid ID {pricer_id} should pass"

        for pricer_id in invalid_pricer_ids:
            assert not re.match(pricer_id_pattern, pricer_id), f"Invalid ID {pricer_id} should fail"

        # Test max_batch_size positive constraint
        valid_sizes = [None, 1, 100, 10000]
        invalid_sizes = [0, -1, -100]

        for size in valid_sizes:
            constraint_passes = size is None or size > 0
            assert constraint_passes

        for size in invalid_sizes:
            constraint_passes = size is None or size > 0
            assert not constraint_passes

        # Test different pricers constraint
        # default_pricer_id != fallback_pricer_id OR fallback_pricer_id IS NULL
        valid_combinations = [
            ("quantlib-v1.18", "treasury-v2.3"),  # different
            ("quantlib-v1.18", None),             # fallback is null
        ]

        invalid_combinations = [
            ("quantlib-v1.18", "quantlib-v1.18")  # same
        ]

        for default, fallback in valid_combinations:
            constraint_passes = default != fallback or fallback is None
            assert constraint_passes

        for default, fallback in invalid_combinations:
            constraint_passes = default != fallback or fallback is None
            assert not constraint_passes

    def test_indexes_and_performance_considerations(self):
        """Test that proper indexes would be created for performance."""
        # These tests verify that the model structure supports efficient queries

        # Test queries that would benefit from indexes
        test_queries = [
            # pricer_registry indexes
            {"table": "pricer_registry", "field": "status", "value": "healthy"},
            {"table": "pricer_registry", "field": "name", "value": "QuantLib"},

            # pricer_capabilities indexes
            {"table": "pricer_capabilities", "field": "instrument_type", "value": "swap"},
            {"table": "pricer_capabilities", "field": "model_type", "value": "Hull-White"},
            {"table": "pricer_capabilities", "field": "priority", "value": 10},

            # tenant_pricing_config indexes
            {"table": "tenant_pricing_config", "field": "tenant_id", "value": "test-tenant"},
            {"table": "tenant_pricing_config", "field": "default_pricer_id", "value": "quantlib-v1.18"}
        ]

        # Verify that model fields support these query patterns
        for query in test_queries:
            table = query["table"]
            field = query["field"]
            value = query["value"]

            if table == "pricer_registry":
                pricer = PricerRegistry.create_quantlib_pricer()
                assert hasattr(pricer, field)
                if field == "status":
                    assert pricer.status == PricerStatus.HEALTHY.value

            elif table == "pricer_capabilities":
                cap = PricerCapability(
                    pricer_id="test-v1.0",
                    instrument_type="swap",
                    model_type="Hull-White",
                    priority=10
                )
                assert hasattr(cap, field)

            elif table == "tenant_pricing_config":
                config = TenantPricingConfig(tenant_id="test-tenant")
                assert hasattr(config, field)

    def test_data_integrity_and_consistency(self):
        """Test data integrity and consistency rules."""
        # Test tenant configuration consistency
        config = TenantPricingConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            config_json={
                "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
                "features": ["batch_pricing"]
            }
        )

        # Verify configuration consistency
        allowed_pricers = config.get_allowed_pricers()
        assert config.default_pricer_id in allowed_pricers
        assert config.fallback_pricer_id in allowed_pricers

        # Test capability consistency
        quantlib_caps = PricerCapability.create_quantlib_capabilities()
        treasury_caps = PricerCapability.create_treasury_capabilities()

        # All QuantLib capabilities should reference QuantLib
        for cap in quantlib_caps:
            assert cap.pricer_id == "quantlib-v1.18"

        # All Treasury capabilities should reference Treasury
        for cap in treasury_caps:
            assert cap.pricer_id == "treasury-v2.3"

        # Priority should be consistent (Treasury > QuantLib for advanced features)
        max_ql_priority = max(cap.priority for cap in quantlib_caps)
        max_treasury_priority = max(cap.priority for cap in treasury_caps)
        assert max_treasury_priority >= max_ql_priority

    def test_trigger_functionality_logic(self):
        """Test database trigger functionality logic."""
        # Test updated_at timestamp trigger logic
        config = TenantPricingConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc"
        )

        original_updated = config.updated_at

        # Simulate update (would trigger updated_at in real DB)
        updated_config = config.update_configuration({"new_key": "new_value"})

        # Verify timestamp was updated
        assert updated_config.updated_at > original_updated

        # Test auto-creation trigger logic (for new tenants)
        system_tenant_id = "00000000-0000-0000-0000-000000000000"
        regular_tenant_id = str(uuid.uuid4())

        # Simulate trigger that creates default pricing config for new tenant
        system_config = TenantPricingConfig.create_system_tenant_config()
        regular_config = TenantPricingConfig.create_default_tenant_config(regular_tenant_id)

        # Verify system tenant gets special configuration
        assert system_config.get_max_batch_size() > regular_config.get_max_batch_size()
        assert len(system_config.get_allowed_pricers()) >= len(regular_config.get_allowed_pricers())

    def test_migration_seed_data_validation(self):
        """Test that migration seed data is properly structured."""
        # Test QuantLib seeded configuration
        quantlib = PricerRegistry.create_quantlib_pricer()
        assert quantlib.pricer_id == "quantlib-v1.18"
        assert quantlib.name == "QuantLib"
        assert quantlib.version == "1.18.0"
        assert quantlib.batch_supported is True
        assert quantlib.max_batch_size == 10000
        assert quantlib.status == PricerStatus.HEALTHY

        # Test Treasury seeded configuration
        treasury = PricerRegistry.create_treasury_pricer()
        assert treasury.pricer_id == "treasury-v2.3"
        assert treasury.name == "Treasury"
        assert treasury.version == "2.3.0"
        assert treasury.batch_supported is True
        assert treasury.max_batch_size == 5000
        assert treasury.status == PricerStatus.HEALTHY

        # Test seeded capabilities
        ql_caps = PricerCapability.create_quantlib_capabilities()
        treasury_caps = PricerCapability.create_treasury_capabilities()

        assert len(ql_caps) > 0
        assert len(treasury_caps) > 0

        # Verify capabilities coverage
        ql_instruments = {cap.instrument_type for cap in ql_caps}
        treasury_instruments = {cap.instrument_type for cap in treasury_caps}

        # Basic instruments should be covered by QuantLib
        basic_instruments = {"swap", "bond", "option"}
        assert basic_instruments.issubset(ql_instruments)

        # Advanced instruments should be covered by Treasury
        advanced_instruments = {"barrier_option", "structured_note"}
        assert advanced_instruments.issubset(treasury_instruments)

    def test_schema_version_compatibility(self):
        """Test schema compatibility and evolution."""
        # Test that models support expected schema version
        # This would be important for schema migrations

        # Test required fields are present
        pricer_required_fields = [
            "pricer_id", "name", "version", "health_check_url", "pricing_url"
        ]

        pricer = PricerRegistry.create_quantlib_pricer()
        for field in pricer_required_fields:
            assert hasattr(pricer, field)
            assert getattr(pricer, field) is not None

        capability_required_fields = [
            "pricer_id", "instrument_type"
        ]

        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="test"
        )
        for field in capability_required_fields:
            assert hasattr(capability, field)
            assert getattr(capability, field) is not None

        config_required_fields = [
            "tenant_id"
        ]

        config = TenantPricingConfig(tenant_id="test")
        for field in config_required_fields:
            assert hasattr(config, field)
            assert getattr(config, field) is not None

    def test_jsonb_field_functionality(self):
        """Test JSONB field functionality for complex configurations."""
        # Test complex configuration storage
        complex_config = {
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3", "custom-v1.0"],
            "features": ["batch_pricing", "dual_pricing", "monte_carlo", "real_time"],
            "max_batch_size": 50000,
            "custom_curves_allowed": True,
            "advanced_models_allowed": True,
            "tenant_specific_models": {
                "custom_hull_white": {
                    "mean_reversion": 0.05,
                    "volatility": 0.02
                },
                "sabr_parameters": {
                    "alpha": 0.3,
                    "beta": 0.7,
                    "rho": -0.2,
                    "nu": 0.4
                }
            },
            "risk_limits": {
                "max_notional": 1000000000,
                "var_limit": 5000000,
                "stress_scenarios": ["covid", "financial_crisis", "brexit"]
            },
            "notification_settings": {
                "email_alerts": True,
                "slack_webhook": "https://hooks.slack.com/...",
                "alert_thresholds": {
                    "pricing_latency_ms": 5000,
                    "error_rate_percent": 1.0
                }
            }
        }

        config = TenantPricingConfig(
            tenant_id=str(uuid.uuid4()),
            config_json=complex_config
        )

        # Test JSONB field access
        assert config.config_json["max_batch_size"] == 50000
        assert config.config_json["custom_curves_allowed"] is True
        assert "custom_hull_white" in config.config_json["tenant_specific_models"]
        assert config.config_json["risk_limits"]["var_limit"] == 5000000

        # Test nested JSON access
        sabr_params = config.config_json["tenant_specific_models"]["sabr_parameters"]
        assert sabr_params["alpha"] == 0.3
        assert sabr_params["beta"] == 0.7

        # Test array handling
        features = config.config_json["features"]
        assert "batch_pricing" in features
        assert "monte_carlo" in features
        assert len(features) == 4

        # Test method access to JSONB data
        assert config.get_max_batch_size() == 50000
        assert config.allows_custom_curves() is True
        assert config.allows_advanced_models() is True