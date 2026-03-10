"""Advanced routing and error handling tests for Registry Service.

These tests cover complex routing scenarios, circuit breaker patterns,
and comprehensive error handling as specified in the technical specification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import asyncio

from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.pricer_capability import PricerCapability
from registry.models.tenant_pricing_config import TenantPricingConfig


class CircuitBreaker:
    """Circuit breaker implementation for pricer health management."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.failure_count: Dict[str, int] = {}
        self.last_failure_time: Dict[str, datetime] = {}
        self.circuit_open: Dict[str, bool] = {}

    def record_failure(self, pricer_id: str) -> None:
        """Record a failure for a pricer."""
        now = datetime.now(timezone.utc)
        self.failure_count[pricer_id] = self.failure_count.get(pricer_id, 0) + 1
        self.last_failure_time[pricer_id] = now

        if self.failure_count[pricer_id] >= self.failure_threshold:
            self.circuit_open[pricer_id] = True

    def record_success(self, pricer_id: str) -> None:
        """Record a success for a pricer."""
        self.failure_count[pricer_id] = 0
        self.circuit_open[pricer_id] = False

    def is_circuit_open(self, pricer_id: str) -> bool:
        """Check if circuit is open for a pricer."""
        if not self.circuit_open.get(pricer_id, False):
            return False

        # Check if recovery timeout has passed
        last_failure = self.last_failure_time.get(pricer_id)
        if last_failure:
            time_since_failure = (datetime.now(timezone.utc) - last_failure).total_seconds()
            if time_since_failure >= self.recovery_timeout:
                # Reset circuit to half-open state (allow one test call)
                self.circuit_open[pricer_id] = False
                return False

        return True

    def get_circuit_status(self, pricer_id: str) -> Dict[str, Any]:
        """Get detailed circuit status for a pricer."""
        return {
            "pricer_id": pricer_id,
            "circuit_open": self.is_circuit_open(pricer_id),
            "failure_count": self.failure_count.get(pricer_id, 0),
            "last_failure": self.last_failure_time.get(pricer_id),
            "threshold": self.failure_threshold
        }


class AdvancedPricingRouter:
    """Advanced routing service with circuit breaker and load balancing."""

    def __init__(self, repository: AsyncMock, circuit_breaker: CircuitBreaker):
        self.repository = repository
        self.circuit_breaker = circuit_breaker

    async def route_pricing_request(
        self,
        tenant_id: str,
        instrument_type: str,
        model_type: Optional[str] = None,
        required_features: Optional[List[str]] = None,
        exclude_pricers: Optional[List[str]] = None
    ) -> Optional[str]:
        """Route pricing request with circuit breaker protection."""
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

        # Exclude specified pricers
        if exclude_pricers:
            valid_capabilities = [
                cap for cap in valid_capabilities
                if cap.pricer_id not in exclude_pricers
            ]

        # Filter by feature requirements
        if required_features:
            valid_capabilities = [
                cap for cap in valid_capabilities
                if all(feature in (cap.features or []) for feature in required_features)
            ]

        if not valid_capabilities:
            return None

        # Sort by priority and check circuit breaker status
        sorted_capabilities = sorted(valid_capabilities, key=lambda c: c.priority, reverse=True)

        for capability in sorted_capabilities:
            pricer_id = capability.pricer_id

            # Check circuit breaker
            if self.circuit_breaker.is_circuit_open(pricer_id):
                continue

            # Check pricer health
            pricer = await self.repository.get_pricer(pricer_id)
            if not pricer or not pricer.is_healthy():
                self.circuit_breaker.record_failure(pricer_id)
                continue

            return pricer_id

        # If no pricers available, try fallback
        if tenant_config.fallback_pricer_id:
            fallback_pricer_id = tenant_config.fallback_pricer_id

            if (fallback_pricer_id not in (exclude_pricers or []) and
                not self.circuit_breaker.is_circuit_open(fallback_pricer_id)):

                fallback_pricer = await self.repository.get_pricer(fallback_pricer_id)
                if fallback_pricer and fallback_pricer.is_healthy():
                    return fallback_pricer_id

        return None

    async def route_dual_pricing_request(
        self,
        tenant_id: str,
        instrument_type: str,
        model_type: Optional[str] = None,
        required_features: Optional[List[str]] = None
    ) -> List[str]:
        """Route to multiple pricers for dual pricing comparison."""
        all_pricers = []

        # Get primary pricer
        primary_pricer = await self.route_pricing_request(
            tenant_id, instrument_type, model_type, required_features
        )
        if primary_pricer:
            all_pricers.append(primary_pricer)

        # Get secondary pricer (exclude the primary)
        secondary_pricer = await self.route_pricing_request(
            tenant_id, instrument_type, model_type, required_features,
            exclude_pricers=[primary_pricer] if primary_pricer else None
        )
        if secondary_pricer:
            all_pricers.append(secondary_pricer)

        return all_pricers

    async def handle_pricing_failure(self, pricer_id: str, error: Exception) -> None:
        """Handle pricing failure and update circuit breaker."""
        self.circuit_breaker.record_failure(pricer_id)

        # Update pricer health status in repository
        pricer = await self.repository.get_pricer(pricer_id)
        if pricer:
            unhealthy_pricer = pricer.mark_unhealthy()
            await self.repository.save_pricer(unhealthy_pricer)

    async def handle_pricing_success(self, pricer_id: str) -> None:
        """Handle pricing success and update circuit breaker."""
        self.circuit_breaker.record_success(pricer_id)

    async def get_routing_analytics(self) -> Dict[str, Any]:
        """Get routing analytics and circuit breaker status."""
        # Get all pricers
        all_pricers = await self.repository.list_pricers()

        circuit_statuses = []
        for pricer in all_pricers:
            status = self.circuit_breaker.get_circuit_status(pricer.pricer_id)
            circuit_statuses.append(status)

        # Count open circuits
        open_circuits = sum(1 for status in circuit_statuses if status["circuit_open"])

        return {
            "total_pricers": len(all_pricers),
            "open_circuits": open_circuits,
            "healthy_pricers": len([p for p in all_pricers if p.is_healthy()]),
            "circuit_statuses": circuit_statuses
        }


class TestCircuitBreakerFunctionality:
    """Test circuit breaker implementation."""

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker with low thresholds for testing."""
        return CircuitBreaker(failure_threshold=3, recovery_timeout=5)

    def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test initial circuit breaker state."""
        pricer_id = "quantlib-v1.18"

        assert not circuit_breaker.is_circuit_open(pricer_id)
        assert circuit_breaker.failure_count.get(pricer_id, 0) == 0

    def test_circuit_breaker_failure_recording(self, circuit_breaker):
        """Test recording failures."""
        pricer_id = "quantlib-v1.18"

        # Record failures up to threshold
        for i in range(2):
            circuit_breaker.record_failure(pricer_id)
            assert not circuit_breaker.is_circuit_open(pricer_id)

        # Third failure should open circuit
        circuit_breaker.record_failure(pricer_id)
        assert circuit_breaker.is_circuit_open(pricer_id)

    def test_circuit_breaker_success_reset(self, circuit_breaker):
        """Test that success resets failure count."""
        pricer_id = "quantlib-v1.18"

        # Record failures
        circuit_breaker.record_failure(pricer_id)
        circuit_breaker.record_failure(pricer_id)
        assert circuit_breaker.failure_count[pricer_id] == 2

        # Record success
        circuit_breaker.record_success(pricer_id)
        assert circuit_breaker.failure_count[pricer_id] == 0
        assert not circuit_breaker.is_circuit_open(pricer_id)

    def test_circuit_breaker_recovery_timeout(self, circuit_breaker):
        """Test circuit recovery after timeout."""
        pricer_id = "quantlib-v1.18"

        # Open the circuit
        for i in range(3):
            circuit_breaker.record_failure(pricer_id)

        assert circuit_breaker.is_circuit_open(pricer_id)

        # Simulate time passing (mock the last failure time)
        past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        circuit_breaker.last_failure_time[pricer_id] = past_time

        # Circuit should now be closed (half-open)
        assert not circuit_breaker.is_circuit_open(pricer_id)

    def test_circuit_breaker_status_reporting(self, circuit_breaker):
        """Test circuit breaker status reporting."""
        pricer_id = "quantlib-v1.18"

        # Record some failures
        circuit_breaker.record_failure(pricer_id)
        circuit_breaker.record_failure(pricer_id)

        status = circuit_breaker.get_circuit_status(pricer_id)

        assert status["pricer_id"] == pricer_id
        assert status["circuit_open"] is False
        assert status["failure_count"] == 2
        assert status["threshold"] == 3
        assert "last_failure" in status


class TestAdvancedRoutingScenarios:
    """Test complex routing scenarios."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker for testing."""
        return CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    @pytest.fixture
    def router(self, mock_repo, circuit_breaker):
        """Advanced pricing router."""
        return AdvancedPricingRouter(mock_repo, circuit_breaker)

    @pytest.fixture
    def tenant_id(self):
        """Test tenant ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_route_pricing_with_circuit_breaker(self, router, mock_repo, tenant_id):
        """Test routing with circuit breaker protection."""
        # Setup tenant config without fallback to test circuit breaker isolation
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)
        tenant_config.fallback_pricer_id = None  # No fallback for this test

        # Setup capabilities
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=10
        )

        # Setup healthy pricer
        pricer = PricerRegistry.create_quantlib_pricer()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]
        mock_repo.get_pricer.return_value = pricer

        # First request should succeed
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )
        assert result == "quantlib-v1.18"

        # Simulate circuit opening
        router.circuit_breaker.record_failure("quantlib-v1.18")
        router.circuit_breaker.record_failure("quantlib-v1.18")
        router.circuit_breaker.record_failure("quantlib-v1.18")

        # Subsequent request should return None due to open circuit
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_route_pricing_with_unhealthy_pricer(self, router, mock_repo, tenant_id):
        """Test routing when pricer is unhealthy."""
        # Setup tenant config with fallback
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)
        tenant_config.fallback_pricer_id = "treasury-v2.3"

        # Setup capabilities
        capabilities = [
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                priority=15
            ),
            PricerCapability(
                pricer_id="treasury-v2.3",
                instrument_type="swap",
                priority=10
            )
        ]

        # Setup pricers - QuantLib unhealthy, Treasury healthy
        unhealthy_quantlib = PricerRegistry.create_quantlib_pricer().mark_unhealthy()
        healthy_treasury = PricerRegistry.create_treasury_pricer()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        def mock_get_pricer(pricer_id):
            if pricer_id == "quantlib-v1.18":
                return unhealthy_quantlib
            elif pricer_id == "treasury-v2.3":
                return healthy_treasury
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Should skip unhealthy QuantLib and use Treasury fallback
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )
        assert result == "treasury-v2.3"

    @pytest.mark.asyncio
    async def test_route_dual_pricing_request(self, router, mock_repo, tenant_id):
        """Test dual pricing routing."""
        # Setup tenant config with both pricers allowed
        tenant_config = TenantPricingConfig.create_system_tenant_config()
        tenant_config.tenant_id = tenant_id

        # Setup capabilities for both pricers
        capabilities = [
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                priority=15
            ),
            PricerCapability(
                pricer_id="treasury-v2.3",
                instrument_type="swap",
                priority=10
            )
        ]

        # Setup healthy pricers
        quantlib_pricer = PricerRegistry.create_quantlib_pricer()
        treasury_pricer = PricerRegistry.create_treasury_pricer()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        def mock_get_pricer(pricer_id):
            if pricer_id == "quantlib-v1.18":
                return quantlib_pricer
            elif pricer_id == "treasury-v2.3":
                return treasury_pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Should return both pricers for dual pricing
        result = await router.route_dual_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        assert len(result) == 2
        assert "quantlib-v1.18" in result  # Higher priority first
        assert "treasury-v2.3" in result

    @pytest.mark.asyncio
    async def test_route_with_feature_filtering(self, router, mock_repo, tenant_id):
        """Test routing with specific feature requirements."""
        # Setup tenant config
        tenant_config = TenantPricingConfig.create_system_tenant_config()
        tenant_config.tenant_id = tenant_id

        # Setup capabilities - only Treasury has monte_carlo
        capabilities = [
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="option",
                features=["greeks", "duration"],
                priority=15
            ),
            PricerCapability(
                pricer_id="treasury-v2.3",
                instrument_type="option",
                features=["greeks", "monte_carlo"],
                priority=10
            )
        ]

        pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        def mock_get_pricer(pricer_id):
            for pricer in pricers:
                if pricer.pricer_id == pricer_id:
                    return pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Request with monte_carlo feature should route to Treasury
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="option",
            required_features=["monte_carlo"]
        )

        assert result == "treasury-v2.3"

    @pytest.mark.asyncio
    async def test_route_with_pricer_exclusion(self, router, mock_repo, tenant_id):
        """Test routing with specific pricers excluded."""
        # Setup tenant config
        tenant_config = TenantPricingConfig.create_system_tenant_config()
        tenant_config.tenant_id = tenant_id

        # Setup capabilities for both pricers
        capabilities = [
            PricerCapability(
                pricer_id="quantlib-v1.18",
                instrument_type="swap",
                priority=15
            ),
            PricerCapability(
                pricer_id="treasury-v2.3",
                instrument_type="swap",
                priority=10
            )
        ]

        pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        def mock_get_pricer(pricer_id):
            for pricer in pricers:
                if pricer.pricer_id == pricer_id:
                    return pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        # Exclude QuantLib, should route to Treasury
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap",
            exclude_pricers=["quantlib-v1.18"]
        )

        assert result == "treasury-v2.3"

    @pytest.mark.asyncio
    async def test_handle_pricing_failure_updates_circuit_breaker(self, router, mock_repo):
        """Test that pricing failures update circuit breaker and pricer status."""
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer()
        unhealthy_pricer = pricer.mark_unhealthy()

        mock_repo.get_pricer.return_value = pricer
        mock_repo.save_pricer.return_value = unhealthy_pricer

        # Handle failure
        await router.handle_pricing_failure(pricer_id, Exception("Pricing failed"))

        # Verify circuit breaker was updated
        assert router.circuit_breaker.failure_count[pricer_id] == 1

        # Verify pricer status was updated
        mock_repo.save_pricer.assert_called_once()
        saved_pricer = mock_repo.save_pricer.call_args[0][0]
        assert saved_pricer.status == PricerStatus.UNHEALTHY.value

    @pytest.mark.asyncio
    async def test_handle_pricing_success_resets_circuit_breaker(self, router, mock_repo):
        """Test that pricing success resets circuit breaker."""
        pricer_id = "quantlib-v1.18"

        # First record some failures
        router.circuit_breaker.record_failure(pricer_id)
        router.circuit_breaker.record_failure(pricer_id)
        assert router.circuit_breaker.failure_count[pricer_id] == 2

        # Handle success
        await router.handle_pricing_success(pricer_id)

        # Verify circuit breaker was reset
        assert router.circuit_breaker.failure_count[pricer_id] == 0
        assert not router.circuit_breaker.is_circuit_open(pricer_id)

    @pytest.mark.asyncio
    async def test_get_routing_analytics(self, router, mock_repo):
        """Test routing analytics generation."""
        # Setup pricers
        pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer().mark_unhealthy()
        ]

        mock_repo.list_pricers.return_value = pricers

        # Record some circuit breaker activity
        router.circuit_breaker.record_failure("quantlib-v1.18")
        router.circuit_breaker.record_failure("treasury-v2.3")
        router.circuit_breaker.record_failure("treasury-v2.3")
        router.circuit_breaker.record_failure("treasury-v2.3")  # Open circuit

        # Get analytics
        analytics = await router.get_routing_analytics()

        assert analytics["total_pricers"] == 2
        assert analytics["healthy_pricers"] == 1  # Only QuantLib is healthy
        assert analytics["open_circuits"] == 1   # Treasury circuit is open
        assert len(analytics["circuit_statuses"]) == 2


class TestErrorHandlingScenarios:
    """Test comprehensive error handling scenarios."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker for testing."""
        return CircuitBreaker()

    @pytest.fixture
    def router(self, mock_repo, circuit_breaker):
        """Advanced pricing router."""
        return AdvancedPricingRouter(mock_repo, circuit_breaker)

    @pytest.mark.asyncio
    async def test_route_with_repository_failure(self, router, mock_repo):
        """Test handling of repository failures."""
        tenant_id = str(uuid4())

        # Simulate repository failure
        mock_repo.get_tenant_pricing_config.side_effect = Exception("Database connection failed")

        # Should handle gracefully
        with pytest.raises(Exception, match="Database connection failed"):
            await router.route_pricing_request(
                tenant_id=tenant_id,
                instrument_type="swap"
            )

    @pytest.mark.asyncio
    async def test_route_with_malformed_tenant_config(self, router, mock_repo):
        """Test handling of malformed tenant configuration."""
        tenant_id = str(uuid4())

        # Create malformed config (missing required fields)
        malformed_config = TenantPricingConfig(tenant_id=tenant_id)
        malformed_config.config_json = None  # This would cause issues

        mock_repo.get_tenant_pricing_config.return_value = malformed_config

        # Should handle gracefully
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        # Should return None rather than crash
        assert result is None

    @pytest.mark.asyncio
    async def test_route_with_corrupted_capability_data(self, router, mock_repo):
        """Test handling of corrupted capability data."""
        tenant_id = str(uuid4())
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Create capability with corrupted features
        corrupted_capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            features=None,  # Corrupted - should be list
            priority=10
        )

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [corrupted_capability]

        # Should handle gracefully without crashing
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap",
            required_features=["greeks"]
        )

        # Should filter out the corrupted capability
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_routing_requests(self, router, mock_repo):
        """Test handling of concurrent routing requests."""
        tenant_id = str(uuid4())
        tenant_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            priority=10
        )

        pricer = PricerRegistry.create_quantlib_pricer()

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = [capability]
        mock_repo.get_pricer.return_value = pricer

        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = router.route_pricing_request(
                tenant_id=tenant_id,
                instrument_type="swap"
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed and return the same pricer
        for result in results:
            assert not isinstance(result, Exception)
            assert result == "quantlib-v1.18"

    @pytest.mark.asyncio
    async def test_circuit_breaker_race_conditions(self, router, mock_repo):
        """Test circuit breaker under concurrent failure scenarios."""
        pricer_id = "quantlib-v1.18"

        # Simulate concurrent failures
        tasks = []
        for i in range(10):
            task = router.handle_pricing_failure(pricer_id, Exception(f"Error {i}"))
            tasks.append(task)

        # Execute concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Circuit should be open after failures
        assert router.circuit_breaker.is_circuit_open(pricer_id)
        assert router.circuit_breaker.failure_count[pricer_id] >= 3


class TestLoadBalancingScenarios:
    """Test load balancing and performance optimization."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker for testing."""
        return CircuitBreaker()

    @pytest.fixture
    def router(self, mock_repo, circuit_breaker):
        """Advanced pricing router."""
        return AdvancedPricingRouter(mock_repo, circuit_breaker)

    @pytest.mark.asyncio
    async def test_priority_based_routing(self, router, mock_repo):
        """Test that routing respects priority ordering."""
        tenant_id = str(uuid4())
        tenant_config = TenantPricingConfig.create_system_tenant_config()
        tenant_config.tenant_id = tenant_id
        # Allow the test pricers
        tenant_config.config_json = {
            "allowed_pricers": ["low-priority-v1.0", "medium-priority-v1.0", "high-priority-v1.0"],
            "features": ["batch_pricing"]
        }

        # Create capabilities with different priorities
        capabilities = [
            PricerCapability(
                pricer_id="low-priority-v1.0",
                instrument_type="swap",
                priority=5
            ),
            PricerCapability(
                pricer_id="medium-priority-v1.0",
                instrument_type="swap",
                priority=10
            ),
            PricerCapability(
                pricer_id="high-priority-v1.0",
                instrument_type="swap",
                priority=15
            )
        ]

        # All pricers are healthy
        healthy_pricer = PricerRegistry(
            pricer_id="test",
            name="Test",
            version="1.0.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY
        )

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities
        mock_repo.get_pricer.return_value = healthy_pricer

        # Should route to highest priority pricer
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        assert result == "high-priority-v1.0"

    @pytest.mark.asyncio
    async def test_cascading_failure_handling(self, router, mock_repo):
        """Test handling of cascading failures across multiple pricers."""
        tenant_id = str(uuid4())
        tenant_config = TenantPricingConfig.create_system_tenant_config()
        tenant_config.tenant_id = tenant_id
        # Allow the test pricers
        tenant_config.config_json = {
            "allowed_pricers": ["pricer-1", "pricer-2", "pricer-3"],
            "features": ["batch_pricing"]
        }

        # Setup multiple capabilities
        capabilities = [
            PricerCapability(pricer_id="pricer-1", instrument_type="swap", priority=15),
            PricerCapability(pricer_id="pricer-2", instrument_type="swap", priority=10),
            PricerCapability(pricer_id="pricer-3", instrument_type="swap", priority=5)
        ]

        mock_repo.get_tenant_pricing_config.return_value = tenant_config
        mock_repo.query_capabilities.return_value = capabilities

        # Simulate all pricers as unhealthy
        unhealthy_pricer = PricerRegistry(
            pricer_id="test",
            name="Test",
            version="1.0.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.UNHEALTHY
        )

        mock_repo.get_pricer.return_value = unhealthy_pricer

        # Should return None when all pricers are unhealthy
        result = await router.route_pricing_request(
            tenant_id=tenant_id,
            instrument_type="swap"
        )

        assert result is None

        # Verify circuit breaker recorded failures for all pricers
        for capability in capabilities:
            assert router.circuit_breaker.failure_count[capability.pricer_id] >= 1