"""Unit tests for IPricerPlugin interface validation.

These tests verify the plugin contract implementation and validation
for the multi-tenant plugin architecture as specified in the technical spec.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json

from registry.models.pricer_registry import PricerRegistry
from registry.models.pricer_capability import PricerCapability


class IPricerPlugin(ABC):
    """
    Plugin contract that all pricers must implement.

    This is the interface specification from the technical docs.
    """

    @abstractmethod
    def get_metadata(self) -> dict:
        """Return pricer metadata for registry registration."""
        pass

    @abstractmethod
    async def price(self, request: dict, tenant_id: str) -> dict:
        """Price single instrument with tenant-specific configuration."""
        pass

    @abstractmethod
    async def price_batch(self, request: dict, tenant_id: str) -> List[dict]:
        """Price multiple instruments in parallel."""
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """Health check for orchestrator to poll."""
        pass


class MockQuantLibPlugin(IPricerPlugin):
    """Mock QuantLib plugin implementation for testing."""

    def __init__(self, health_status: str = "healthy"):
        self.health_status = health_status
        self.pricing_call_count = 0
        self.batch_call_count = 0

    def get_metadata(self) -> dict:
        """Return QuantLib metadata."""
        return {
            "pricer_id": "quantlib-v1.18",
            "name": "QuantLib",
            "version": "1.18.0",
            "capabilities": [
                {
                    "instrument_type": "swap",
                    "model_type": "Hull-White",
                    "features": ["greeks", "duration", "convexity"],
                    "priority": 10
                },
                {
                    "instrument_type": "bond",
                    "model_type": "Yield",
                    "features": ["yield", "duration"],
                    "priority": 9
                }
            ],
            "health_check_url": "http://quantlib-service:8088/health",
            "pricing_url": "http://quantlib-service:8088/api/v1",
            "batch_supported": True,
            "max_batch_size": 10000
        }

    async def price(self, request: dict, tenant_id: str) -> dict:
        """Mock pricing implementation."""
        self.pricing_call_count += 1

        if not tenant_id:
            raise ValueError("tenant_id is required")

        instrument_type = request.get("instrument_type")
        if not instrument_type:
            raise ValueError("instrument_type is required")

        # Simulate different pricing based on instrument type
        if instrument_type == "swap":
            return {
                "instrument_type": "swap",
                "npv": 12345.67,
                "duration": 4.23,
                "convexity": 18.91,
                "tenant_id": tenant_id,
                "pricer": "quantlib-v1.18",
                "calculation_time_ms": 87
            }
        elif instrument_type == "bond":
            return {
                "instrument_type": "bond",
                "npv": 1023.45,
                "yield": 0.0378,
                "duration": 3.2,
                "tenant_id": tenant_id,
                "pricer": "quantlib-v1.18",
                "calculation_time_ms": 45
            }
        else:
            raise ValueError(f"Unsupported instrument type: {instrument_type}")

    async def price_batch(self, request: dict, tenant_id: str) -> List[dict]:
        """Mock batch pricing implementation."""
        self.batch_call_count += 1

        if not tenant_id:
            raise ValueError("tenant_id is required")

        instruments = request.get("instruments", [])
        if not instruments:
            return []

        if len(instruments) > 10000:
            raise ValueError("Batch size exceeds maximum of 10000")

        results = []
        for i, instrument in enumerate(instruments):
            try:
                result = await self.price(instrument, tenant_id)
                result["index"] = i
                results.append(result)
            except Exception as e:
                results.append({
                    "index": i,
                    "error": {
                        "error_code": "PRICING_ERROR",
                        "detail": str(e)
                    }
                })

        return results

    async def health_check(self) -> dict:
        """Mock health check."""
        return {
            "status": self.health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.18.0",
            "pricing_calls": self.pricing_call_count,
            "batch_calls": self.batch_call_count
        }


class MockTreasuryPlugin(IPricerPlugin):
    """Mock Treasury plugin implementation for testing."""

    def __init__(self, health_status: str = "healthy"):
        self.health_status = health_status

    def get_metadata(self) -> dict:
        """Return Treasury metadata."""
        return {
            "pricer_id": "treasury-v2.3",
            "name": "Treasury",
            "version": "2.3.0",
            "capabilities": [
                {
                    "instrument_type": "swap",
                    "model_type": "SABR",
                    "features": ["greeks", "volatility_smile", "monte_carlo"],
                    "priority": 12
                },
                {
                    "instrument_type": "barrier_option",
                    "model_type": "Monte-Carlo",
                    "features": ["greeks", "monte_carlo", "barrier_monitoring"],
                    "priority": 15
                }
            ],
            "health_check_url": "http://treasury-service:8101/health",
            "pricing_url": "http://treasury-service:8101/api/v1",
            "batch_supported": True,
            "max_batch_size": 5000
        }

    async def price(self, request: dict, tenant_id: str) -> dict:
        """Mock Treasury pricing with Monte Carlo."""
        if self.health_status != "healthy":
            raise Exception("Service unhealthy")

        instrument_type = request.get("instrument_type")
        if instrument_type == "barrier_option":
            return {
                "instrument_type": "barrier_option",
                "npv": 8765.43,
                "delta": 0.65,
                "gamma": 0.012,
                "vega": 45.2,
                "monte_carlo_paths": 100000,
                "tenant_id": tenant_id,
                "pricer": "treasury-v2.3",
                "calculation_time_ms": 1250
            }
        else:
            return {
                "instrument_type": instrument_type,
                "npv": 15000.0,
                "tenant_id": tenant_id,
                "pricer": "treasury-v2.3",
                "calculation_time_ms": 500
            }

    async def price_batch(self, request: dict, tenant_id: str) -> List[dict]:
        """Mock Treasury batch pricing."""
        if self.health_status != "healthy":
            raise Exception("Service unhealthy")

        instruments = request.get("instruments", [])
        if len(instruments) > 5000:
            raise ValueError("Batch size exceeds Treasury maximum of 5000")

        # Simulate parallel processing delay
        results = []
        for i, instrument in enumerate(instruments):
            result = await self.price(instrument, tenant_id)
            result["index"] = i
            results.append(result)

        return results

    async def health_check(self) -> dict:
        """Mock Treasury health check."""
        return {
            "status": self.health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.3.0",
            "monte_carlo_engine": "enabled",
            "pde_solver": "enabled"
        }


class PluginValidator:
    """Validator for plugin interface compliance."""

    @staticmethod
    def validate_metadata(metadata: dict) -> List[str]:
        """Validate plugin metadata structure."""
        errors = []

        # Required fields
        required_fields = ["pricer_id", "name", "version", "health_check_url", "pricing_url"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")

        # Validate pricer_id format
        if "pricer_id" in metadata:
            pricer_id = metadata["pricer_id"]
            if not isinstance(pricer_id, str) or not pricer_id:
                errors.append("pricer_id must be a non-empty string")

        # Validate capabilities
        if "capabilities" in metadata:
            capabilities = metadata["capabilities"]
            if not isinstance(capabilities, list):
                errors.append("capabilities must be a list")
            else:
                for i, cap in enumerate(capabilities):
                    cap_errors = PluginValidator._validate_capability(cap, i)
                    errors.extend(cap_errors)

        # Validate batch settings
        if metadata.get("batch_supported"):
            if "max_batch_size" not in metadata:
                errors.append("max_batch_size required when batch_supported is True")
            elif not isinstance(metadata["max_batch_size"], int) or metadata["max_batch_size"] <= 0:
                errors.append("max_batch_size must be a positive integer")

        return errors

    @staticmethod
    def _validate_capability(capability: dict, index: int) -> List[str]:
        """Validate individual capability structure."""
        errors = []
        prefix = f"capabilities[{index}]"

        required_fields = ["instrument_type"]
        for field in required_fields:
            if field not in capability:
                errors.append(f"{prefix}: Missing required field {field}")

        if "instrument_type" in capability:
            if not isinstance(capability["instrument_type"], str) or not capability["instrument_type"]:
                errors.append(f"{prefix}: instrument_type must be a non-empty string")

        if "features" in capability:
            features = capability["features"]
            if not isinstance(features, list):
                errors.append(f"{prefix}: features must be a list")
            elif not all(isinstance(f, str) for f in features):
                errors.append(f"{prefix}: all features must be strings")

        if "priority" in capability:
            priority = capability["priority"]
            if not isinstance(priority, int):
                errors.append(f"{prefix}: priority must be an integer")

        return errors

    @staticmethod
    async def validate_plugin_compliance(plugin: IPricerPlugin) -> List[str]:
        """Validate that a plugin implements the interface correctly."""
        errors = []

        # Test metadata
        try:
            metadata = plugin.get_metadata()
            metadata_errors = PluginValidator.validate_metadata(metadata)
            errors.extend(metadata_errors)
        except Exception as e:
            errors.append(f"get_metadata() failed: {str(e)}")

        # Test health check
        try:
            health = await plugin.health_check()
            if not isinstance(health, dict):
                errors.append("health_check() must return a dictionary")
            elif "status" not in health:
                errors.append("health_check() result must include 'status' field")
        except Exception as e:
            errors.append(f"health_check() failed: {str(e)}")

        # Test basic pricing (if plugin appears healthy)
        try:
            test_request = {
                "instrument_type": "swap",
                "notional": 1000000,
                "tenor": "5Y"
            }
            result = await plugin.price(test_request, "test-tenant")
            if not isinstance(result, dict):
                errors.append("price() must return a dictionary")
        except Exception as e:
            errors.append(f"price() failed: {str(e)}")

        # Test batch pricing
        try:
            batch_request = {
                "instruments": [
                    {"instrument_type": "swap", "notional": 1000000},
                    {"instrument_type": "bond", "face_value": 1000}
                ]
            }
            results = await plugin.price_batch(batch_request, "test-tenant")
            if not isinstance(results, list):
                errors.append("price_batch() must return a list")
        except Exception as e:
            errors.append(f"price_batch() failed: {str(e)}")

        return errors


class TestPluginInterfaceValidation:
    """Test plugin interface compliance validation."""

    def test_validate_valid_quantlib_metadata(self):
        """Test validation of valid QuantLib metadata."""
        plugin = MockQuantLibPlugin()
        metadata = plugin.get_metadata()

        errors = PluginValidator.validate_metadata(metadata)
        assert errors == []

    def test_validate_valid_treasury_metadata(self):
        """Test validation of valid Treasury metadata."""
        plugin = MockTreasuryPlugin()
        metadata = plugin.get_metadata()

        errors = PluginValidator.validate_metadata(metadata)
        assert errors == []

    def test_validate_metadata_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_metadata = {
            "name": "Test Pricer",
            # Missing pricer_id, version, health_check_url, pricing_url
        }

        errors = PluginValidator.validate_metadata(invalid_metadata)

        assert len(errors) == 4
        assert any("pricer_id" in error for error in errors)
        assert any("version" in error for error in errors)
        assert any("health_check_url" in error for error in errors)
        assert any("pricing_url" in error for error in errors)

    def test_validate_metadata_invalid_capabilities(self):
        """Test validation with invalid capabilities."""
        invalid_metadata = {
            "pricer_id": "test-v1.0",
            "name": "Test",
            "version": "1.0.0",
            "health_check_url": "http://test:8080/health",
            "pricing_url": "http://test:8080/api/v1",
            "capabilities": [
                {},  # Missing instrument_type
                {
                    "instrument_type": "",  # Empty string
                    "features": "not_a_list",  # Should be list
                    "priority": "not_an_int"  # Should be int
                }
            ]
        }

        errors = PluginValidator.validate_metadata(invalid_metadata)

        assert len(errors) >= 4
        assert any("Missing required field instrument_type" in error for error in errors)
        assert any("instrument_type must be a non-empty string" in error for error in errors)
        assert any("features must be a list" in error for error in errors)
        assert any("priority must be an integer" in error for error in errors)

    def test_validate_metadata_batch_settings(self):
        """Test validation of batch-related settings."""
        # Missing max_batch_size when batch_supported is True
        invalid_metadata = {
            "pricer_id": "test-v1.0",
            "name": "Test",
            "version": "1.0.0",
            "health_check_url": "http://test:8080/health",
            "pricing_url": "http://test:8080/api/v1",
            "batch_supported": True
            # Missing max_batch_size
        }

        errors = PluginValidator.validate_metadata(invalid_metadata)
        assert any("max_batch_size required when batch_supported is True" in error for error in errors)

        # Invalid max_batch_size
        invalid_metadata["max_batch_size"] = -100
        errors = PluginValidator.validate_metadata(invalid_metadata)
        assert any("max_batch_size must be a positive integer" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validate_quantlib_plugin_compliance(self):
        """Test full compliance validation for QuantLib plugin."""
        plugin = MockQuantLibPlugin()

        errors = await PluginValidator.validate_plugin_compliance(plugin)
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_treasury_plugin_compliance(self):
        """Test full compliance validation for Treasury plugin."""
        plugin = MockTreasuryPlugin()

        errors = await PluginValidator.validate_plugin_compliance(plugin)
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_unhealthy_plugin_compliance(self):
        """Test validation of unhealthy plugin."""
        plugin = MockTreasuryPlugin(health_status="unhealthy")

        errors = await PluginValidator.validate_plugin_compliance(plugin)

        # Should have errors for pricing methods due to unhealthy status
        assert len(errors) >= 2
        assert any("price() failed" in error for error in errors)
        assert any("price_batch() failed" in error for error in errors)


class TestPluginFunctionality:
    """Test plugin functionality and behavior."""

    @pytest.mark.asyncio
    async def test_quantlib_plugin_single_pricing(self):
        """Test QuantLib plugin single instrument pricing."""
        plugin = MockQuantLibPlugin()

        # Test swap pricing
        swap_request = {
            "instrument_type": "swap",
            "notional": 1000000,
            "fixed_rate": 0.03,
            "tenor": "5Y"
        }

        result = await plugin.price(swap_request, "tenant-123")

        assert result["instrument_type"] == "swap"
        assert result["npv"] == 12345.67
        assert result["duration"] == 4.23
        assert result["tenant_id"] == "tenant-123"
        assert result["pricer"] == "quantlib-v1.18"
        assert "calculation_time_ms" in result

    @pytest.mark.asyncio
    async def test_quantlib_plugin_batch_pricing(self):
        """Test QuantLib plugin batch pricing."""
        plugin = MockQuantLibPlugin()

        batch_request = {
            "instruments": [
                {"instrument_type": "swap", "notional": 1000000},
                {"instrument_type": "bond", "face_value": 1000},
                {"instrument_type": "invalid_type"}  # Should cause error
            ]
        }

        results = await plugin.price_batch(batch_request, "tenant-123")

        assert len(results) == 3

        # First result should be successful
        assert results[0]["index"] == 0
        assert results[0]["instrument_type"] == "swap"
        assert results[0]["tenant_id"] == "tenant-123"

        # Second result should be successful
        assert results[1]["index"] == 1
        assert results[1]["instrument_type"] == "bond"
        assert results[1]["tenant_id"] == "tenant-123"

        # Third result should have error
        assert results[2]["index"] == 2
        assert "error" in results[2]
        assert results[2]["error"]["error_code"] == "PRICING_ERROR"

    @pytest.mark.asyncio
    async def test_quantlib_plugin_batch_size_limit(self):
        """Test QuantLib plugin respects batch size limits."""
        plugin = MockQuantLibPlugin()

        # Create batch exceeding limit
        large_batch = {
            "instruments": [{"instrument_type": "swap"}] * 10001
        }

        with pytest.raises(ValueError, match="Batch size exceeds maximum"):
            await plugin.price_batch(large_batch, "tenant-123")

    @pytest.mark.asyncio
    async def test_plugin_tenant_validation(self):
        """Test that plugins validate tenant_id requirement."""
        plugin = MockQuantLibPlugin()

        # Test with empty tenant_id
        with pytest.raises(ValueError, match="tenant_id is required"):
            await plugin.price({"instrument_type": "swap"}, "")

        with pytest.raises(ValueError, match="tenant_id is required"):
            await plugin.price_batch({"instruments": []}, "")

    @pytest.mark.asyncio
    async def test_treasury_plugin_exotic_instruments(self):
        """Test Treasury plugin handling exotic instruments."""
        plugin = MockTreasuryPlugin()

        barrier_request = {
            "instrument_type": "barrier_option",
            "barrier_type": "knock_in",
            "barrier_level": 105.0,
            "spot": 100.0
        }

        result = await plugin.price(barrier_request, "tenant-456")

        assert result["instrument_type"] == "barrier_option"
        assert result["npv"] == 8765.43
        assert "monte_carlo_paths" in result
        assert result["monte_carlo_paths"] == 100000
        assert result["tenant_id"] == "tenant-456"

    @pytest.mark.asyncio
    async def test_plugin_health_monitoring(self):
        """Test plugin health check functionality."""
        plugin = MockQuantLibPlugin()

        # Do some pricing calls to affect metrics
        await plugin.price({"instrument_type": "swap"}, "tenant-1")
        await plugin.price_batch({"instruments": [{"instrument_type": "bond"}]}, "tenant-1")

        health = await plugin.health_check()

        assert health["status"] == "healthy"
        assert health["version"] == "1.18.0"
        assert health["pricing_calls"] == 2  # One from price, one from price_batch
        assert health["batch_calls"] == 1
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_treasury_plugin_unhealthy_behavior(self):
        """Test Treasury plugin behavior when unhealthy."""
        plugin = MockTreasuryPlugin(health_status="unhealthy")

        # Health check should still work
        health = await plugin.health_check()
        assert health["status"] == "unhealthy"

        # But pricing should fail
        with pytest.raises(Exception, match="Service unhealthy"):
            await plugin.price({"instrument_type": "swap"}, "tenant-1")

        with pytest.raises(Exception, match="Service unhealthy"):
            await plugin.price_batch({"instruments": []}, "tenant-1")


class TestPluginRegistrationWorkflow:
    """Test the complete plugin registration workflow."""

    @pytest.mark.asyncio
    async def test_register_quantlib_plugin_from_metadata(self):
        """Test creating registry entries from plugin metadata."""
        plugin = MockQuantLibPlugin()
        metadata = plugin.get_metadata()

        # Convert plugin metadata to registry models
        pricer_registry = PricerRegistry(
            pricer_id=metadata["pricer_id"],
            name=metadata["name"],
            version=metadata["version"],
            health_check_url=metadata["health_check_url"],
            pricing_url=metadata["pricing_url"],
            batch_supported=metadata["batch_supported"],
            max_batch_size=metadata["max_batch_size"]
        )

        capabilities = []
        for cap_data in metadata["capabilities"]:
            capability = PricerCapability(
                pricer_id=metadata["pricer_id"],
                instrument_type=cap_data["instrument_type"],
                model_type=cap_data.get("model_type"),
                features=cap_data.get("features", []),
                priority=cap_data.get("priority", 0)
            )
            capabilities.append(capability)

        # Verify registry entries match plugin metadata
        assert pricer_registry.pricer_id == "quantlib-v1.18"
        assert pricer_registry.name == "QuantLib"
        assert pricer_registry.batch_supported is True
        assert pricer_registry.max_batch_size == 10000

        assert len(capabilities) == 2
        assert capabilities[0].instrument_type == "swap"
        assert capabilities[0].model_type == "Hull-White"
        assert "greeks" in capabilities[0].features

    def test_capability_matching_logic(self):
        """Test capability matching logic used by orchestrator."""
        # Create capabilities from plugin metadata
        plugin = MockQuantLibPlugin()
        metadata = plugin.get_metadata()

        capabilities = []
        for cap_data in metadata["capabilities"]:
            capability = PricerCapability(
                pricer_id=metadata["pricer_id"],
                instrument_type=cap_data["instrument_type"],
                model_type=cap_data.get("model_type"),
                features=cap_data.get("features", []),
                priority=cap_data.get("priority", 0)
            )
            capabilities.append(capability)

        # Test matching logic
        swap_cap = capabilities[0]  # First capability is swap

        # Should match exact requirements
        assert swap_cap.matches_requirements("swap", "Hull-White", ["greeks"])
        assert swap_cap.matches_requirements("swap", "Hull-White", ["duration"])

        # Should not match different instrument
        assert not swap_cap.matches_requirements("bond", "Hull-White", ["greeks"])

        # Should not match different model
        assert not swap_cap.matches_requirements("swap", "Black-Scholes", ["greeks"])

        # Should not match missing features
        assert not swap_cap.matches_requirements("swap", "Hull-White", ["monte_carlo"])

        # Should match when no model specified
        assert swap_cap.matches_requirements("swap", None, ["greeks"])

        # Should match when no features specified
        assert swap_cap.matches_requirements("swap", "Hull-White", None)