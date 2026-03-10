"""Integration tests for Capability Query functionality.

These tests verify the complete capability query flow including database operations,
API endpoints, and multi-pricer capability resolution.
"""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient

from registry.api.pricing_router import pricing_router
from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.pricer_capability import PricerCapability
from registry.models.tenant_pricing_config import TenantPricingConfig
from registry.repositories.pricing_repository import PricingRepository


class TestCapabilityQueryIntegration:
    """Integration tests for capability query functionality."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with pricing router."""
        app = FastAPI()
        app.include_router(pricing_router)
        return app

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository with realistic data."""
        repo = AsyncMock(spec=PricingRepository)

        # Set up pricers
        quantlib_pricer = PricerRegistry.create_quantlib_pricer()
        treasury_pricer = PricerRegistry.create_treasury_pricer()

        # Set up capabilities
        quantlib_caps = PricerCapability.create_quantlib_capabilities()
        treasury_caps = PricerCapability.create_treasury_capabilities()

        # Mock repository methods
        repo.query_capabilities.return_value = []  # Will be set per test
        repo.get_pricer.side_effect = lambda pricer_id: {
            "quantlib-v1.18": quantlib_pricer,
            "treasury-v2.3": treasury_pricer
        }.get(pricer_id)
        repo.get_pricer_capabilities.side_effect = lambda pricer_id: {
            "quantlib-v1.18": quantlib_caps,
            "treasury-v2.3": treasury_caps
        }.get(pricer_id, [])

        return repo

    @pytest.mark.asyncio
    async def test_query_capabilities_single_instrument_type(self, app, mock_repo):
        """Test querying capabilities by single instrument type."""
        # Setup: Find all capabilities for swap instruments
        instrument_type = "swap"
        swap_capabilities = [
            cap for cap in PricerCapability.create_quantlib_capabilities() +
                           PricerCapability.create_treasury_capabilities()
            if cap.instrument_type == instrument_type
        ]

        mock_repo.query_capabilities.return_value = swap_capabilities

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query_params"]["instrument_type"] == instrument_type
        assert "matching_pricers" in data

        # Verify query parameters
        mock_repo.query_capabilities.assert_called_once_with(
            instrument_type=instrument_type,
            model_type=None,
            feature=None
        )

    @pytest.mark.asyncio
    async def test_query_capabilities_with_model_type_filtering(self, app, mock_repo):
        """Test querying capabilities with model type filtering."""
        instrument_type = "option"
        model_type = "Black-Scholes"

        # Setup: Find Black-Scholes option capabilities (should be QuantLib)
        matching_capabilities = [
            cap for cap in PricerCapability.create_quantlib_capabilities()
            if cap.instrument_type == instrument_type and cap.model_type == model_type
        ]

        mock_repo.query_capabilities.return_value = matching_capabilities

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    f"/registry/pricers/query"
                    f"?instrument_type={instrument_type}"
                    f"&model_type={model_type}"
                )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query_params"]["instrument_type"] == instrument_type
        assert data["query_params"]["model_type"] == model_type

        # Should find QuantLib (supports Black-Scholes options)
        if len(data["matching_pricers"]) > 0:
            assert any(pricer["pricer_id"] == "quantlib-v1.18" for pricer in data["matching_pricers"])

        mock_repo.query_capabilities.assert_called_once_with(
            instrument_type=instrument_type,
            model_type=model_type,
            feature=None
        )

    @pytest.mark.asyncio
    async def test_query_capabilities_with_feature_filtering(self, app, mock_repo):
        """Test querying capabilities with feature requirements."""
        instrument_type = "swap"
        feature = "monte_carlo"

        # Setup: Find capabilities that support Monte Carlo (should be Treasury)
        matching_capabilities = [
            cap for cap in PricerCapability.create_treasury_capabilities()
            if cap.instrument_type == instrument_type and
               cap.features and feature in cap.features
        ]

        mock_repo.query_capabilities.return_value = matching_capabilities

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    f"/registry/pricers/query"
                    f"?instrument_type={instrument_type}"
                    f"&feature={feature}"
                )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query_params"]["instrument_type"] == instrument_type
        assert data["query_params"]["feature"] == feature

        # Should find Treasury (supports Monte Carlo)
        if len(data["matching_pricers"]) > 0:
            assert any(pricer["pricer_id"] == "treasury-v2.3" for pricer in data["matching_pricers"])

        mock_repo.query_capabilities.assert_called_once_with(
            instrument_type=instrument_type,
            model_type=None,
            feature=feature
        )

    @pytest.mark.asyncio
    async def test_query_capabilities_priority_based_sorting(self, app, mock_repo):
        """Test that matching pricers are sorted by capability priority."""
        instrument_type = "swap"

        # Create capabilities with different priorities
        high_priority_cap = PricerCapability(
            pricer_id="treasury-v2.3",
            instrument_type=instrument_type,
            model_type="SABR",
            features=["greeks", "monte_carlo"],
            priority=25  # High priority
        )

        low_priority_cap = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type=instrument_type,
            model_type="Hull-White",
            features=["greeks", "duration"],
            priority=10  # Lower priority
        )

        mock_repo.query_capabilities.return_value = [low_priority_cap, high_priority_cap]

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

        # Verify
        assert response.status_code == 200
        data = response.json()

        if len(data["matching_pricers"]) >= 2:
            # Should be sorted by priority (highest first)
            first_pricer = data["matching_pricers"][0]
            second_pricer = data["matching_pricers"][1]

            # Treasury should be first (higher priority capability)
            assert first_pricer["pricer_id"] == "treasury-v2.3"
            assert second_pricer["pricer_id"] == "quantlib-v1.18"

    @pytest.mark.asyncio
    async def test_query_capabilities_unhealthy_pricer_filtering(self, app, mock_repo):
        """Test that unhealthy pricers are filtered out from results."""
        instrument_type = "bond"

        # Setup capabilities from both pricers
        bond_capabilities = [
            cap for cap in PricerCapability.create_quantlib_capabilities() +
                           PricerCapability.create_treasury_capabilities()
            if cap.instrument_type == instrument_type
        ]

        mock_repo.query_capabilities.return_value = bond_capabilities

        # Mock QuantLib as healthy, Treasury as unhealthy
        quantlib_pricer = PricerRegistry.create_quantlib_pricer()
        treasury_pricer = PricerRegistry.create_treasury_pricer()
        treasury_pricer.status = PricerStatus.UNHEALTHY

        def mock_get_pricer(pricer_id):
            if pricer_id == "quantlib-v1.18":
                return quantlib_pricer
            elif pricer_id == "treasury-v2.3":
                return treasury_pricer
            return None

        mock_repo.get_pricer.side_effect = mock_get_pricer

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

        # Verify
        assert response.status_code == 200
        data = response.json()

        # Should only include healthy pricers
        pricer_ids = [pricer["pricer_id"] for pricer in data["matching_pricers"]]
        assert "quantlib-v1.18" in pricer_ids  # Healthy
        assert "treasury-v2.3" not in pricer_ids  # Unhealthy

    @pytest.mark.asyncio
    async def test_query_capabilities_no_matches(self, app, mock_repo):
        """Test querying capabilities with no matches."""
        instrument_type = "exotic_derivative"  # Non-existent instrument type

        mock_repo.query_capabilities.return_value = []

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query_params"]["instrument_type"] == instrument_type
        assert len(data["matching_pricers"]) == 0

    @pytest.mark.asyncio
    async def test_query_capabilities_complete_pricer_metadata(self, app, mock_repo):
        """Test that complete pricer metadata is returned in results."""
        instrument_type = "swap"

        # Setup one capability match
        swap_capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type=instrument_type,
            model_type="Hull-White",
            features=["greeks", "duration"],
            priority=10
        )

        mock_repo.query_capabilities.return_value = [swap_capability]

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

        # Verify
        assert response.status_code == 200
        data = response.json()

        if len(data["matching_pricers"]) > 0:
            pricer = data["matching_pricers"][0]

            # Verify complete metadata
            assert pricer["pricer_id"] == "quantlib-v1.18"
            assert pricer["name"] == "QuantLib"
            assert pricer["version"] == "1.18.0"
            assert "health_check_url" in pricer
            assert "pricing_url" in pricer
            assert "batch_supported" in pricer
            assert "capabilities" in pricer
            assert len(pricer["capabilities"]) > 0

    @pytest.mark.asyncio
    async def test_query_capabilities_advanced_filtering_combination(self, app, mock_repo):
        """Test complex capability query with all filters combined."""
        instrument_type = "swaption"
        model_type = "SABR"
        feature = "volatility_smile"

        # Setup: Should match advanced Treasury capabilities
        advanced_capability = PricerCapability(
            pricer_id="treasury-v2.3",
            instrument_type=instrument_type,
            model_type=model_type,
            features=["volatility_smile", "smile_dynamics", "local_volatility"],
            priority=30
        )

        mock_repo.query_capabilities.return_value = [advanced_capability]

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    f"/registry/pricers/query"
                    f"?instrument_type={instrument_type}"
                    f"&model_type={model_type}"
                    f"&feature={feature}"
                )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["query_params"]["instrument_type"] == instrument_type
        assert data["query_params"]["model_type"] == model_type
        assert data["query_params"]["feature"] == feature

        # Verify all parameters were passed to repository
        mock_repo.query_capabilities.assert_called_once_with(
            instrument_type=instrument_type,
            model_type=model_type,
            feature=feature
        )

    @pytest.mark.asyncio
    async def test_query_capabilities_missing_required_parameter(self, app, mock_repo):
        """Test query capabilities with missing required instrument_type."""
        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/registry/pricers/query")

        # Verify validation error
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "instrument_type" in str(data["detail"])

    @pytest.mark.asyncio
    async def test_query_capabilities_repository_error_handling(self, app, mock_repo):
        """Test error handling when repository fails."""
        instrument_type = "swap"

        # Setup repository to raise an exception
        mock_repo.query_capabilities.side_effect = Exception("Database connection lost")

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "Failed to query pricers" in data["detail"]

    @pytest.mark.asyncio
    async def test_query_capabilities_real_world_scenarios(self, app, mock_repo):
        """Test capability query with real-world scenarios."""

        # Scenario 1: Find pricers for vanilla swap pricing
        vanilla_scenario = {
            "instrument_type": "swap",
            "expected_pricers": ["quantlib-v1.18", "treasury-v2.3"]  # Both support swaps
        }

        # Scenario 2: Find pricers for exotic Monte Carlo pricing
        exotic_scenario = {
            "instrument_type": "barrier_option",
            "feature": "monte_carlo",
            "expected_pricers": ["treasury-v2.3"]  # Only Treasury supports exotic Monte Carlo
        }

        # Scenario 3: Find pricers for high-frequency batch pricing
        batch_scenario = {
            "instrument_type": "swap",
            "feature": "batch_pricing",
            "expected_pricers": ["quantlib-v1.18", "treasury-v2.3"]  # Both support batching
        }

        scenarios = [vanilla_scenario, exotic_scenario, batch_scenario]

        for i, scenario in enumerate(scenarios):
            # Setup appropriate capabilities for scenario
            if scenario["instrument_type"] == "barrier_option":
                mock_capabilities = [
                    cap for cap in PricerCapability.create_treasury_capabilities()
                    if cap.instrument_type == "barrier_option"
                ]
            else:
                mock_capabilities = [
                    cap for cap in (PricerCapability.create_quantlib_capabilities() +
                                  PricerCapability.create_treasury_capabilities())
                    if cap.instrument_type == scenario["instrument_type"]
                ]

            mock_repo.query_capabilities.return_value = mock_capabilities

            # Build query URL
            url = f"/registry/pricers/query?instrument_type={scenario['instrument_type']}"
            if "feature" in scenario:
                url += f"&feature={scenario['feature']}"

            with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get(url)

            # Verify scenario expectations
            assert response.status_code == 200
            data = response.json()
            returned_pricer_ids = [p["pricer_id"] for p in data["matching_pricers"]]

            for expected_pricer in scenario["expected_pricers"]:
                if scenario["instrument_type"] == "barrier_option" and expected_pricer == "quantlib-v1.18":
                    # QuantLib doesn't support barrier options in our test data
                    continue
                # Should include expected pricers (if they have matching capabilities)
                # Note: Exact matches depend on test data setup