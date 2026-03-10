"""Simplified unit tests for Registry Service business logic.

These tests focus on testing the business logic without full SQLAlchemy model dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone


class MockPricerRegistry:
    """Mock PricerRegistry for testing without SQLAlchemy."""

    def __init__(self, pricer_id: str, name: str, status: str = "healthy"):
        self.pricer_id = pricer_id
        self.name = name
        self.status = status
        self.health_check_failures = 0

    def is_healthy(self) -> bool:
        return self.status == "healthy"

    def mark_unhealthy(self):
        new_instance = MockPricerRegistry(self.pricer_id, self.name, "unhealthy")
        new_instance.health_check_failures = self.health_check_failures + 1
        return new_instance

    def mark_healthy(self):
        new_instance = MockPricerRegistry(self.pricer_id, self.name, "healthy")
        new_instance.health_check_failures = 0
        return new_instance

    @classmethod
    def create_quantlib_pricer(cls):
        return cls("quantlib-v1.18", "QuantLib", "healthy")

    @classmethod
    def create_treasury_pricer(cls):
        return cls("treasury-v2.3", "Treasury", "healthy")


class MockPricerCapability:
    """Mock PricerCapability for testing without SQLAlchemy."""

    def __init__(self, pricer_id: str, instrument_type: str, model_type: str = None,
                 features: list = None, priority: int = 0):
        self.pricer_id = pricer_id
        self.instrument_type = instrument_type
        self.model_type = model_type
        self.features = features or []
        self.priority = priority

    def matches_requirements(self, instrument_type: str, model_type: str = None,
                           required_features: list = None) -> bool:
        if self.instrument_type != instrument_type:
            return False

        # If capability has a specific model_type, it must match the requested model_type
        # If capability has model_type=None, it matches any requested model_type (wildcard)
        if model_type and self.model_type and self.model_type != model_type:
            return False

        if required_features:
            if not all(feature in self.features for feature in required_features):
                return False

        return True


class MockTenantPricingConfig:
    """Mock TenantPricingConfig for testing without SQLAlchemy."""

    def __init__(self, tenant_id: str, default_pricer_id: str = None,
                 fallback_pricer_id: str = None, allowed_pricers: list = None):
        self.tenant_id = tenant_id
        self.default_pricer_id = default_pricer_id
        self.fallback_pricer_id = fallback_pricer_id
        self._allowed_pricers = allowed_pricers or ["quantlib-v1.18"]

    def get_allowed_pricers(self) -> list:
        return self._allowed_pricers

    @classmethod
    def create_default_tenant_config(cls, tenant_id: str):
        return cls(
            tenant_id=tenant_id,
            default_pricer_id="quantlib-v1.18",
            fallback_pricer_id="treasury-v2.3",
            allowed_pricers=["quantlib-v1.18"]
        )


class SimplifiedPricingService:
    """Simplified pricing service for testing core business logic."""

    def __init__(self, repository: AsyncMock):
        self.repository = repository

    async def find_best_pricer_for_request(self, tenant_id: str, instrument_type: str,
                                         model_type: str = None, required_features: list = None):
        """Find the best pricer for a pricing request."""
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

        # Check feature requirements
        if required_features:
            valid_capabilities = [
                cap for cap in valid_capabilities
                if all(feature in cap.features for feature in required_features)
            ]

        if not valid_capabilities:
            return None

        # Get highest priority healthy pricer
        for capability in sorted(valid_capabilities, key=lambda c: c.priority, reverse=True):
            pricer = await self.repository.get_pricer(capability.pricer_id)
            if pricer and pricer.is_healthy():
                return pricer.pricer_id

        return None


class TestSimplifiedPricingService:
    """Test simplified pricing service business logic."""

    @pytest.fixture
    def mock_repo(self):
        """Mock repository."""
        return AsyncMock()

    @pytest.fixture
    def pricing_service(self, mock_repo):
        """Pricing service instance."""
        return SimplifiedPricingService(mock_repo)

    @pytest.fixture
    def tenant_id(self):
        """Test tenant ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_find_best_pricer_success(self, pricing_service, mock_repo, tenant_id):
        """Test successful pricer selection."""
        # Setup
        tenant_config = MockTenantPricingConfig.create_default_tenant_config(tenant_id)

        capability = MockPricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            features=["greeks"],
            priority=10
        )

        pricer = MockPricerRegistry.create_quantlib_pricer()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]
        mock_repo.get_pricer.return_value = pricer

        # Execute
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Verify
        assert result == "quantlib-v1.18"

    @pytest.mark.asyncio
    async def test_find_best_pricer_tenant_not_found(self, pricing_service, mock_repo, tenant_id):
        """Test routing when tenant config not found."""
        mock_repo.get_tenant_pricing_config.return_value = None

        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_best_pricer_no_capabilities(self, pricing_service, mock_repo, tenant_id):
        """Test routing when no capabilities match."""
        tenant_config = MockTenantPricingConfig.create_default_tenant_config(tenant_id)

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = []  # No matching capabilities

        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="exotic_instrument"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_best_pricer_feature_filtering(self, pricing_service, mock_repo, tenant_id):
        """Test that feature requirements are enforced."""
        tenant_config = MockTenantPricingConfig(
            tenant_id=tenant_id,
            allowed_pricers=["quantlib-v1.18", "treasury-v2.3"]
        )

        capabilities = [
            MockPricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="option",
                features=["greeks"],
                priority=15
            ),
            MockPricerCapability(
                pricer_id="treasury-v2.3",
                instrument_type="option",
                features=["greeks", "monte_carlo"],
                priority=10
            )
        ]

        pricers = [
            MockPricerRegistry.create_quantlib_pricer(),
            MockPricerRegistry.create_treasury_pricer()
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        def mock_get_pricer(pricer_id):
            for pricer in pricers:
                if pricer.pricer_id == pricer_id:
                    return pricer
            return None
        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Request requiring monte_carlo should route to Treasury
        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="option",
            required_features=["monte_carlo"]
        )

        assert result == "treasury-v2.3"

    @pytest.mark.asyncio
    async def test_find_best_pricer_unhealthy_pricer(self, pricing_service, mock_repo, tenant_id):
        """Test routing skips unhealthy pricers."""
        tenant_config = MockTenantPricingConfig.create_default_tenant_config(tenant_id)

        capability = MockPricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=10
        )

        unhealthy_pricer = MockPricerRegistry.create_quantlib_pricer().mark_unhealthy()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]
        mock_repo.get_pricer.return_value = unhealthy_pricer

        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_best_pricer_priority_ordering(self, pricing_service, mock_repo, tenant_id):
        """Test that pricers are selected by priority."""
        tenant_config = MockTenantPricingConfig(
            tenant_id=tenant_id,
            allowed_pricers=["low-priority", "high-priority"]
        )

        capabilities = [
            MockPricerCapability(
                pricer_id="low-priority",
                instrument_type="swap",
                priority=5
            ),
            MockPricerCapability(
                pricer_id="high-priority",
                instrument_type="swap",
                priority=15
            )
        ]

        pricers = [
            MockPricerRegistry("low-priority", "Low Priority", "healthy"),
            MockPricerRegistry("high-priority", "High Priority", "healthy")
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        def mock_get_pricer(pricer_id):
            for pricer in pricers:
                if pricer.pricer_id == pricer_id:
                    return pricer
            return None
        mock_repo.get_pricer.side_effect = mock_get_pricer

        result = await pricing_service.find_best_pricer_for_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Should select high-priority pricer
        assert result == "high-priority"


class TestPricerCapabilityMatching:
    """Test capability matching logic."""

    def test_capability_matches_exact_requirements(self):
        """Test capability matching with exact requirements."""
        capability = MockPricerCapability(
            pricer_id="test",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration", "convexity"]
        )

        # Exact match should work
        assert capability.matches_requirements("swap", "Hull-White", ["greeks"])
        assert capability.matches_requirements("swap", "Hull-White", ["duration"])
        assert capability.matches_requirements("swap", "Hull-White", ["greeks", "duration"])

        # Wrong instrument should not match
        assert not capability.matches_requirements("bond", "Hull-White", ["greeks"])

        # Wrong model should not match
        assert not capability.matches_requirements("swap", "Black-Scholes", ["greeks"])

        # Missing feature should not match
        assert not capability.matches_requirements("swap", "Hull-White", ["monte_carlo"])

    def test_capability_matches_no_model_specified(self):
        """Test capability matching when no model is specified."""
        capability = MockPricerCapability(
            pricer_id="test",
            instrument_type="swap",
            features=["greeks"]
        )

        # Should match when no model required
        assert capability.matches_requirements("swap", None, ["greeks"])
        assert capability.matches_requirements("swap", None, None)

        # Should match even when specific model is requested (None = any model)
        assert capability.matches_requirements("swap", "Hull-White", ["greeks"])

    def test_capability_matches_no_features_required(self):
        """Test capability matching when no features are required."""
        capability = MockPricerCapability(
            pricer_id="test",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration"]
        )

        # Should match when no features required
        assert capability.matches_requirements("swap", "Hull-White", None)
        assert capability.matches_requirements("swap", "Hull-White", [])


class TestMockModels:
    """Test mock model behavior."""

    def test_mock_pricer_registry_health_management(self):
        """Test mock pricer health state changes."""
        pricer = MockPricerRegistry.create_quantlib_pricer()

        assert pricer.is_healthy()
        assert pricer.status == "healthy"
        assert pricer.health_check_failures == 0

        # Mark unhealthy
        unhealthy = pricer.mark_unhealthy()
        assert not unhealthy.is_healthy()
        assert unhealthy.status == "unhealthy"
        assert unhealthy.health_check_failures == 1

        # Mark healthy again
        healthy_again = unhealthy.mark_healthy()
        assert healthy_again.is_healthy()
        assert healthy_again.status == "healthy"
        assert healthy_again.health_check_failures == 0

    def test_mock_tenant_config_allowed_pricers(self):
        """Test mock tenant config pricer management."""
        tenant_id = str(uuid4())
        config = MockTenantPricingConfig.create_default_tenant_config(tenant_id)

        assert config.tenant_id == tenant_id
        assert config.default_pricer_id == "quantlib-v1.18"
        assert "quantlib-v1.18" in config.get_allowed_pricers()

        # Test with custom allowed pricers
        custom_config = MockTenantPricingConfig(
            tenant_id=tenant_id,
            allowed_pricers=["quantlib-v1.18", "treasury-v2.3"]
        )
        allowed = custom_config.get_allowed_pricers()
        assert len(allowed) == 2
        assert "quantlib-v1.18" in allowed
        assert "treasury-v2.3" in allowed