"""Unit tests for Pricing Service business logic layer.

These tests verify the business logic orchestration between repository,
routing, and capability management for the pricing infrastructure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import List, Optional

from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.pricer_capability import PricerCapability
from registry.models.tenant_pricing_config import TenantPricingConfig


class MockPricingService:
    """Mock pricing service for testing business logic without external dependencies."""

    def __init__(self, repository: AsyncMock):
        self.repository = repository

    async def register_pricer_with_capabilities(
        self,
        pricer: PricerRegistry,
        capabilities: List[PricerCapability]
    ) -> PricerRegistry:
        """Register a pricer along with its capabilities."""
        # Save pricer first
        saved_pricer = await self.repository.save_pricer(pricer)

        # Delete existing capabilities
        await self.repository.delete_pricer_capabilities(pricer.pricer_id)

        # Save new capabilities
        for capability in capabilities:
            capability.pricer_id = saved_pricer.pricer_id
            await self.repository.save_capability(capability)

        return saved_pricer

    async def find_best_pricer_for_request(
        self,
        tenant_id: str,
        instrument_type: str,
        model_type: Optional[str] = None,
        required_features: Optional[List[str]] = None
    ) -> Optional[str]:
        """Find the best pricer for a pricing request based on tenant config and capabilities."""
        # Get tenant configuration
        tenant_config = await self.repository.get_tenant_pricing_config(tenant_id)
        if not tenant_config:
            return None

        # Query capabilities
        capabilities = await self.repository.query_capabilities(
            instrument_type=instrument_type,
            model_type=model_type,
            feature=required_features[0] if required_features else None
        )

        # Filter by tenant-allowed pricers
        allowed_pricers = tenant_config.get_allowed_pricers()
        valid_capabilities = [
            cap for cap in capabilities
            if cap.pricer_id in allowed_pricers
        ]

        if not valid_capabilities:
            return None

        # Check if specific features are required
        if required_features:
            valid_capabilities = [
                cap for cap in valid_capabilities
                if all(feature in (cap.features or []) for feature in required_features)
            ]

        if not valid_capabilities:
            return None

        # Get the highest priority healthy pricer
        for capability in sorted(valid_capabilities, key=lambda c: c.priority, reverse=True):
            pricer = await self.repository.get_pricer(capability.pricer_id)
            if pricer and pricer.is_healthy():
                return pricer.pricer_id

        # Fall back to tenant's fallback pricer if configured
        if tenant_config.fallback_pricer_id:
            fallback_pricer = await self.repository.get_pricer(tenant_config.fallback_pricer_id)
            if fallback_pricer and fallback_pricer.is_healthy():
                return tenant_config.fallback_pricer_id

        return None

    async def update_pricer_health_status(
        self,
        pricer_id: str,
        is_healthy: bool,
        timestamp: datetime
    ) -> Optional[PricerRegistry]:
        """Update a pricer's health status."""
        pricer = await self.repository.get_pricer(pricer_id)
        if not pricer:
            return None

        if is_healthy:
            updated_pricer = pricer.mark_healthy()
        else:
            updated_pricer = pricer.mark_unhealthy()

        updated_pricer.last_health_check = timestamp
        return await self.repository.save_pricer(updated_pricer)

    async def get_pricer_registry_stats(self) -> dict:
        """Get comprehensive registry statistics."""
        return await self.repository.get_pricer_statistics()


class TestPricingServiceRegistration:
    """Test pricer registration business logic."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def pricing_service(self, mock_repo):
        """Pricing service instance."""
        return MockPricingService(mock_repo)

    @pytest.mark.asyncio
    async def test_register_pricer_with_capabilities_success(self, pricing_service, mock_repo):
        """Test successful pricer registration with capabilities."""
        # Setup
        pricer = PricerRegistry.create_quantlib_pricer()
        capabilities = PricerCapability.create_quantlib_capabilities()[:3]

        mock_repo.save_pricer.return_value = pricer
        mock_repo.delete_pricer_capabilities.return_value = 0
        mock_repo.save_capability.return_value = AsyncMock()

        # Execute
        result = await pricing_service.register_pricer_with_capabilities(pricer, capabilities)

        # Verify
        assert result == pricer
        mock_repo.save_pricer.assert_called_once_with(pricer)
        mock_repo.delete_pricer_capabilities.assert_called_once_with(pricer.pricer_id)
        assert mock_repo.save_capability.call_count == 3

        # Verify each capability was set with the correct pricer_id
        for call in mock_repo.save_capability.call_args_list:
            saved_capability = call[0][0]
            assert saved_capability.pricer_id == pricer.pricer_id

    @pytest.mark.asyncio
    async def test_register_pricer_with_capabilities_repository_failure(self, pricing_service, mock_repo):
        """Test handling of repository failure during registration."""
        # Setup
        pricer = PricerRegistry.create_quantlib_pricer()
        capabilities = PricerCapability.create_quantlib_capabilities()[:2]

        mock_repo.save_pricer.side_effect = Exception("Database error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database error"):
            await pricing_service.register_pricer_with_capabilities(pricer, capabilities)

        # Verify pricer save was attempted but capability operations were not
        mock_repo.save_pricer.assert_called_once_with(pricer)
        mock_repo.delete_pricer_capabilities.assert_not_called()
        mock_repo.save_capability.assert_not_called()


class TestPricingServiceRouting:
    """Test capability-based routing logic."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def pricing_service(self, mock_repo):
        """Pricing service instance."""
        return MockPricingService(mock_repo)

    @pytest.fixture
    def tenant_id(self):
        """Test tenant ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_find_best_pricer_success(self, pricing_service, mock_repo, tenant_id):
        """Test successful pricer selection based on capabilities and tenant config."""
        # Setup
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Create capabilities with different priorities
        high_priority_cap = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration"],
            priority=15
        )

        low_priority_cap = PricerCapability(
            pricer_id="treasury-v2.3",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks"],
            priority=10
        )

        # Create corresponding pricers
        quantlib_pricer = PricerRegistry.create_quantlib_pricer()
        treasury_pricer = PricerRegistry.create_treasury_pricer()

        # Mock repository responses
        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [low_priority_cap, high_priority_cap]

        def mock_get_pricer(pricer_id):
            if pricer_id == "quantlib-v1.18":
                return quantlib_pricer
            elif pricer_id == "treasury-v2.3":
                return treasury_pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap",
            model_type="Hull-White",
            required_features=["greeks"]
        )

        # Verify - Should select highest priority pricer (QuantLib)
        assert result == "quantlib-v1.18"

        mock_repo.get_tenant_pricing_config.assert_called_once_with(tenant_id)
        mock_repo.query_capabilities.assert_called_once_with(
            instrument_type="swap",
            model_type="Hull-White",
            feature="greeks"
        )

    @pytest.mark.asyncio
    async def test_find_best_pricer_tenant_not_found(self, pricing_service, mock_repo, tenant_id):
        """Test routing when tenant configuration is not found."""
        # Setup
        mock_repo.get_tenant_pricing_config.return_value = None

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Verify
        assert result is None
        mock_repo.get_tenant_pricing_config.assert_called_once_with(tenant_id)
        mock_repo.query_capabilities.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_best_pricer_no_matching_capabilities(self, pricing_service, mock_repo, tenant_id):
        """Test routing when no capabilities match the request."""
        # Setup
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = []  # No matching capabilities

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="exotic_option"  # Unsupported instrument
        )

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_find_best_pricer_with_feature_filtering(self, pricing_service, mock_repo, tenant_id):
        """Test that pricers are correctly filtered by required features."""
        # Setup
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)
        # Allow both pricers so we can test feature filtering
        tenant_config.config_json = {
            "allowed_pricers": ["quantlib-v1.18", "treasury-v2.3"],
            "features": ["batch_pricing"]
        }

        # Capability without required feature
        no_monte_carlo_cap = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="option",
            features=["greeks", "duration"],
            priority=10
        )

        # Capability with required feature
        monte_carlo_cap = PricerCapability(
            pricer_id="treasury-v2.3",
            instrument_type="option",
            features=["greeks", "monte_carlo"],
            priority=8
        )

        pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [no_monte_carlo_cap, monte_carlo_cap]

        def mock_get_pricer(pricer_id):
            for pricer in pricers:
                if pricer.pricer_id == pricer_id:
                    return pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="option",
            required_features=["monte_carlo"]
        )

        # Verify - Should select Treasury even though it has lower priority
        # because it's the only one with monte_carlo feature
        assert result == "treasury-v2.3"

    @pytest.mark.asyncio
    async def test_find_best_pricer_fallback_to_tenant_fallback(self, pricing_service, mock_repo, tenant_id):
        """Test fallback to tenant's fallback pricer when primary options are unavailable."""
        # Setup
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)
        tenant_config.fallback_pricer_id = "treasury-v2.3"

        # Capability exists but pricer is unhealthy
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=10
        )

        unhealthy_quantlib = PricerRegistry.create_quantlib_pricer().mark_unhealthy()
        healthy_treasury = PricerRegistry.create_treasury_pricer()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]

        def mock_get_pricer(pricer_id):
            if pricer_id == "quantlib-v1.18":
                return unhealthy_quantlib
            elif pricer_id == "treasury-v2.3":
                return healthy_treasury
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Verify - Should fall back to Treasury
        assert result == "treasury-v2.3"

    @pytest.mark.asyncio
    async def test_find_best_pricer_respects_tenant_allowed_pricers(self, pricing_service, mock_repo, tenant_id):
        """Test that only tenant-allowed pricers are considered."""
        # Setup - Tenant only allowed to use QuantLib
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)
        # Default config only allows quantlib-v1.18

        # Both pricers have capabilities, but Treasury is not allowed
        quantlib_cap = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=5
        )

        treasury_cap = PricerCapability(
            pricer_id="treasury-v2.3",
            instrument_type="swap",
            priority=15  # Higher priority but not allowed
        )

        pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [treasury_cap, quantlib_cap]

        def mock_get_pricer(pricer_id):
            for pricer in pricers:
                if pricer.pricer_id == pricer_id:
                    return pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Verify - Should select QuantLib despite lower priority
        # because Treasury is not in allowed_pricers list
        assert result == "quantlib-v1.18"


class TestPricingServiceHealthManagement:
    """Test health monitoring business logic."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def pricing_service(self, mock_repo):
        """Pricing service instance."""
        return MockPricingService(mock_repo)

    @pytest.mark.asyncio
    async def test_update_pricer_health_status_healthy(self, pricing_service, mock_repo):
        """Test updating pricer to healthy status."""
        # Setup
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer().mark_unhealthy()
        timestamp = datetime.now(timezone.utc)

        healthy_pricer = pricer.mark_healthy()
        healthy_pricer.last_health_check = timestamp

        mock_repo.get_pricer.return_value = pricer
        mock_repo.save_pricer.return_value = healthy_pricer

        # Execute
        result = await pricing_service.update_pricer_health_status(
            pricer_id=pricer_id,
            is_healthy=True,
            timestamp=timestamp
        )

        # Verify
        assert result == healthy_pricer
        assert result.status == PricerStatus.HEALTHY.value
        assert result.last_health_check == timestamp
        assert result.health_check_failures == 0

        mock_repo.get_pricer.assert_called_once_with(pricer_id)
        mock_repo.save_pricer.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_pricer_health_status_unhealthy(self, pricing_service, mock_repo):
        """Test updating pricer to unhealthy status."""
        # Setup
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer()  # Starts healthy
        timestamp = datetime.now(timezone.utc)

        unhealthy_pricer = pricer.mark_unhealthy()
        unhealthy_pricer.last_health_check = timestamp

        mock_repo.get_pricer.return_value = pricer
        mock_repo.save_pricer.return_value = unhealthy_pricer

        # Execute
        result = await pricing_service.update_pricer_health_status(
            pricer_id=pricer_id,
            is_healthy=False,
            timestamp=timestamp
        )

        # Verify
        assert result == unhealthy_pricer
        assert result.status == PricerStatus.UNHEALTHY.value
        assert result.last_health_check == timestamp
        assert result.health_check_failures == 1  # Incremented

        mock_repo.get_pricer.assert_called_once_with(pricer_id)
        mock_repo.save_pricer.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_pricer_health_status_pricer_not_found(self, pricing_service, mock_repo):
        """Test updating health for non-existent pricer."""
        # Setup
        pricer_id = "non-existent-v1.0"
        timestamp = datetime.now(timezone.utc)

        mock_repo.get_pricer.return_value = None

        # Execute
        result = await pricing_service.update_pricer_health_status(
            pricer_id=pricer_id,
            is_healthy=True,
            timestamp=timestamp
        )

        # Verify
        assert result is None
        mock_repo.get_pricer.assert_called_once_with(pricer_id)
        mock_repo.save_pricer.assert_not_called()


class TestPricingServiceAnalytics:
    """Test analytics and statistics functionality."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def pricing_service(self, mock_repo):
        """Pricing service instance."""
        return MockPricingService(mock_repo)

    @pytest.mark.asyncio
    async def test_get_pricer_registry_stats(self, pricing_service, mock_repo):
        """Test getting comprehensive registry statistics."""
        # Setup
        expected_stats = {
            "total_pricers": 2,
            "healthy_pricers": 2,
            "unhealthy_pricers": 0,
            "total_capabilities": 15,
            "instruments_supported": 5,
            "instrument_capability_counts": {
                "swap": 6,
                "bond": 3,
                "option": 4,
                "swaption": 2
            }
        }

        mock_repo.get_pricer_statistics.return_value = expected_stats

        # Execute
        result = await pricing_service.get_pricer_registry_stats()

        # Verify
        assert result == expected_stats
        mock_repo.get_pricer_statistics.assert_called_once()


class TestPricingServiceEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def pricing_service(self, mock_repo):
        """Pricing service instance."""
        return MockPricingService(mock_repo)

    @pytest.mark.asyncio
    async def test_find_best_pricer_all_pricers_unhealthy(self, pricing_service, mock_repo):
        """Test routing when all matching pricers are unhealthy."""
        # Setup
        tenant_id = str(uuid4())
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=10
        )

        unhealthy_pricer = PricerRegistry.create_quantlib_pricer().mark_unhealthy()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]
        mock_repo.get_pricer.return_value = unhealthy_pricer

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Verify - Should return None since no healthy pricers available
        assert result is None

    @pytest.mark.asyncio
    async def test_find_best_pricer_empty_allowed_pricers_list(self, pricing_service, mock_repo):
        """Test routing when tenant has empty allowed pricers list."""
        # Setup
        tenant_id = str(uuid4())
        tenant_config = TenantPricingConfig(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            config_json={"allowed_pricers": []}  # Empty list
        )

        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=10
        )

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Verify - Should return None since no pricers are allowed
        assert result is None