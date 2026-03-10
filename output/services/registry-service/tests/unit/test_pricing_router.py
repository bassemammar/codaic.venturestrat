"""Unit tests for Pricing Router endpoints.

These tests verify the REST API endpoints for pricing service registration,
capability discovery, and tenant pricing configuration management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from registry.api.pricing_router import (
    pricing_router,
    PricerRegistrationRequest,
    PricerCapabilityModel,
    TenantPricingConfigRequest
)
from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.pricer_capability import PricerCapability
from registry.models.tenant_pricing_config import TenantPricingConfig


# Test app setup
app = FastAPI()
app.include_router(pricing_router)


class TestPricerRegistrationEndpoints:
    """Test pricer registration endpoints."""

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    def test_register_pricer_success(self, client, mock_repo):
        """Test successful pricer registration."""
        # Setup
        request_data = {
            "pricer_id": "test-pricer-v1.0",
            "name": "Test Pricer",
            "version": "1.0.0",
            "description": "Test pricing service",
            "health_check_url": "http://test-pricer:8080/health",
            "pricing_url": "http://test-pricer:8080/api/v1",
            "batch_supported": True,
            "max_batch_size": 1000,
            "capabilities": [
                {
                    "instrument_type": "swap",
                    "model_type": "Hull-White",
                    "features": ["greeks", "duration"],
                    "priority": 10
                }
            ]
        }

        saved_pricer = PricerRegistry(
            pricer_id=request_data["pricer_id"],
            name=request_data["name"],
            version=request_data["version"]
        )
        saved_pricer.created_at = "2026-01-10T14:30:00Z"

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.save_pricer.return_value = saved_pricer
            mock_repo.save_capability.return_value = AsyncMock()

            # Execute
            response = client.post("/registry/pricers", json=request_data)

            # Verify
            assert response.status_code == 201
            data = response.json()
            assert data["pricer_id"] == request_data["pricer_id"]
            assert data["status"] == "registered"
            assert "registered_at" in data

    def test_register_pricer_conflict(self, client, mock_repo):
        """Test pricer registration conflict."""
        # Setup
        request_data = {
            "pricer_id": "existing-pricer-v1.0",
            "name": "Existing Pricer",
            "version": "1.0.0",
            "health_check_url": "http://existing:8080/health",
            "pricing_url": "http://existing:8080/api/v1",
            "capabilities": []
        }

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.save_pricer.side_effect = Exception("already exists")

            # Execute
            response = client.post("/registry/pricers", json=request_data)

            # Verify
            assert response.status_code == 409  # Conflict
            data = response.json()
            assert "already registered" in data["detail"]

    def test_list_pricers_success(self, client, mock_repo):
        """Test successful listing of pricers."""
        # Setup
        pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]
        capabilities = PricerCapability.create_quantlib_capabilities()[:2]

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.list_pricers.return_value = pricers
            mock_repo.get_pricer_capabilities.return_value = capabilities

            # Execute
            response = client.get("/registry/pricers")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["total_pricers"] == 2
            assert len(data["pricers"]) == 2

            # Check first pricer
            first_pricer = data["pricers"][0]
            assert first_pricer["pricer_id"] == "quantlib-v1.18"
            assert first_pricer["name"] == "QuantLib"
            assert len(first_pricer["capabilities"]) == 2

    def test_list_pricers_with_status_filter(self, client, mock_repo):
        """Test listing pricers with status filter."""
        # Setup
        healthy_pricers = [PricerRegistry.create_quantlib_pricer()]

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.list_pricers.return_value = healthy_pricers
            mock_repo.get_pricer_capabilities.return_value = []

            # Execute
            response = client.get("/registry/pricers?status=healthy")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["total_pricers"] == 1

            # Verify that status filter was applied
            mock_repo.list_pricers.assert_called_with(status="healthy")

    def test_get_pricer_success(self, client, mock_repo):
        """Test successful get pricer by ID."""
        # Setup
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer()
        capabilities = PricerCapability.create_quantlib_capabilities()[:3]

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.get_pricer.return_value = pricer
            mock_repo.get_pricer_capabilities.return_value = capabilities

            # Execute
            response = client.get(f"/registry/pricers/{pricer_id}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["pricer_id"] == pricer_id
            assert data["name"] == "QuantLib"
            assert len(data["capabilities"]) == 3

    def test_get_pricer_not_found(self, client, mock_repo):
        """Test get pricer not found."""
        # Setup
        pricer_id = "non-existent-v1.0"

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.get_pricer.return_value = None

            # Execute
            response = client.get(f"/registry/pricers/{pricer_id}")

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]


class TestCapabilityQueryEndpoints:
    """Test capability query endpoints."""

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    def test_query_pricers_by_instrument(self, client, mock_repo):
        """Test querying pricers by instrument type."""
        # Setup
        instrument_type = "swap"
        capabilities = [
            cap for cap in PricerCapability.create_quantlib_capabilities()
            if cap.instrument_type == instrument_type
        ]
        pricer = PricerRegistry.create_quantlib_pricer()

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.query_capabilities.return_value = capabilities
            mock_repo.get_pricer.return_value = pricer
            mock_repo.get_pricer_capabilities.return_value = capabilities

            # Execute
            response = client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["query_params"]["instrument_type"] == instrument_type
            assert len(data["matching_pricers"]) >= 0

            # Verify query was called with correct parameters
            mock_repo.query_capabilities.assert_called_with(
                instrument_type=instrument_type,
                model_type=None,
                feature=None
            )

    def test_query_pricers_with_model_and_feature(self, client, mock_repo):
        """Test querying pricers with model type and feature requirements."""
        # Setup
        instrument_type = "option"
        model_type = "Black-Scholes"
        feature = "greeks"
        capabilities = []  # No matches for specific criteria

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.query_capabilities.return_value = capabilities

            # Execute
            response = client.get(
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
            assert len(data["matching_pricers"]) == 0

            # Verify query was called with correct parameters
            mock_repo.query_capabilities.assert_called_with(
                instrument_type=instrument_type,
                model_type=model_type,
                feature=feature
            )

    def test_query_pricers_with_priority_sorting(self, client, mock_repo):
        """Test that matching pricers are sorted by priority."""
        # Setup
        instrument_type = "swap"

        # Create capabilities with different priorities
        high_priority_cap = PricerCapability(
            pricer_id="high-priority-v1.0",
            instrument_type="swap",
            priority=20
        )
        low_priority_cap = PricerCapability(
            pricer_id="low-priority-v1.0",
            instrument_type="swap",
            priority=5
        )

        # Create corresponding pricers
        high_priority_pricer = PricerRegistry(
            pricer_id="high-priority-v1.0",
            name="High Priority",
            version="1.0.0",
            health_check_url="http://high:8080/health",
            pricing_url="http://high:8080/api/v1",
            status=PricerStatus.HEALTHY
        )

        low_priority_pricer = PricerRegistry(
            pricer_id="low-priority-v1.0",
            name="Low Priority",
            version="1.0.0",
            health_check_url="http://low:8080/health",
            pricing_url="http://low:8080/api/v1",
            status=PricerStatus.HEALTHY
        )

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.query_capabilities.return_value = [low_priority_cap, high_priority_cap]

            # Mock get_pricer to return appropriate pricer based on ID
            def mock_get_pricer(pricer_id):
                if pricer_id == "high-priority-v1.0":
                    return high_priority_pricer
                elif pricer_id == "low-priority-v1.0":
                    return low_priority_pricer
                return None

            mock_repo.get_pricer.side_effect = mock_get_pricer

            # Mock get_pricer_capabilities to return single capability
            def mock_get_capabilities(pricer_id):
                if pricer_id == "high-priority-v1.0":
                    return [high_priority_cap]
                elif pricer_id == "low-priority-v1.0":
                    return [low_priority_cap]
                return []

            mock_repo.get_pricer_capabilities.side_effect = mock_get_capabilities

            # Execute
            response = client.get(f"/registry/pricers/query?instrument_type={instrument_type}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert len(data["matching_pricers"]) == 2

            # Verify that pricers are sorted by priority (highest first)
            first_pricer = data["matching_pricers"][0]
            second_pricer = data["matching_pricers"][1]

            assert first_pricer["pricer_id"] == "high-priority-v1.0"
            assert second_pricer["pricer_id"] == "low-priority-v1.0"

    def test_query_pricers_missing_instrument_type(self, client):
        """Test query pricers with missing required instrument_type parameter."""
        # Execute
        response = client.get("/registry/pricers/query")

        # Verify
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "instrument_type" in str(data["detail"])


class TestHealthManagementEndpoints:
    """Test health management endpoints."""

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    def test_update_pricer_health_success(self, client, mock_repo):
        """Test successful health status update."""
        # Setup
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer()
        updated_pricer = pricer.mark_healthy()

        request_data = {
            "status": "healthy",
            "timestamp": "2026-01-10T14:30:00Z"
        }

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.get_pricer.return_value = pricer
            mock_repo.save_pricer.return_value = updated_pricer

            # Execute
            response = client.put(f"/registry/pricers/{pricer_id}/health", json=request_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["pricer_id"] == pricer_id
            assert data["status"] == "healthy"
            assert "updated_at" in data

    def test_update_pricer_health_unhealthy(self, client, mock_repo):
        """Test updating pricer to unhealthy status."""
        # Setup
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer()
        updated_pricer = pricer.mark_unhealthy()

        request_data = {
            "status": "unhealthy",
            "timestamp": "2026-01-10T14:30:00Z"
        }

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.get_pricer.return_value = pricer
            mock_repo.save_pricer.return_value = updated_pricer

            # Execute
            response = client.put(f"/registry/pricers/{pricer_id}/health", json=request_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["pricer_id"] == pricer_id
            assert data["status"] == "unhealthy"

    def test_update_pricer_health_not_found(self, client, mock_repo):
        """Test updating health for non-existent pricer."""
        # Setup
        pricer_id = "non-existent-v1.0"
        request_data = {
            "status": "healthy",
            "timestamp": "2026-01-10T14:30:00Z"
        }

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo):
            mock_repo.get_pricer.return_value = None

            # Execute
            response = client.put(f"/registry/pricers/{pricer_id}/health", json=request_data)

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]


class TestTenantPricingConfigEndpoints:
    """Test tenant pricing configuration endpoints."""

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_repo(self):
        """Mock pricing repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_tenant_service(self):
        """Mock tenant service."""
        return AsyncMock()

    def test_get_tenant_pricing_config_existing(self, client, mock_repo, mock_tenant_service):
        """Test getting existing tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())
        tenant = MagicMock()
        config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo), \
             patch('registry.api.pricing_router.get_tenant_service', return_value=mock_tenant_service):

            mock_tenant_service.get_tenant_by_id.return_value = tenant
            mock_repo.get_tenant_pricing_config.return_value = config

            # Execute
            response = client.get(f"/registry/tenants/{tenant_id}/pricing-config")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == tenant_id
            assert data["default_pricer_id"] == "quantlib-v1.18"

    def test_get_tenant_pricing_config_create_default(self, client, mock_repo, mock_tenant_service):
        """Test getting tenant pricing config with auto-creation of default."""
        # Setup
        tenant_id = str(uuid4())
        tenant = MagicMock()
        default_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo), \
             patch('registry.api.pricing_router.get_tenant_service', return_value=mock_tenant_service):

            mock_tenant_service.get_tenant_by_id.return_value = tenant
            mock_repo.get_tenant_pricing_config.return_value = None  # No existing config
            mock_repo.save_tenant_pricing_config.return_value = default_config

            # Execute
            response = client.get(f"/registry/tenants/{tenant_id}/pricing-config")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == tenant_id

            # Verify that default config was created
            mock_repo.save_tenant_pricing_config.assert_called_once()

    def test_get_tenant_pricing_config_tenant_not_found(self, client, mock_repo, mock_tenant_service):
        """Test getting config for non-existent tenant."""
        # Setup
        tenant_id = str(uuid4())

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo), \
             patch('registry.api.pricing_router.get_tenant_service', return_value=mock_tenant_service):

            mock_tenant_service.get_tenant_by_id.return_value = None

            # Execute
            response = client.get(f"/registry/tenants/{tenant_id}/pricing-config")

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]

    def test_update_tenant_pricing_config_success(self, client, mock_repo, mock_tenant_service):
        """Test successful tenant pricing configuration update."""
        # Setup
        tenant_id = str(uuid4())
        tenant = MagicMock()
        existing_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        request_data = {
            "default_pricer_id": "treasury-v2.3",
            "max_batch_size": 2000,
            "features": ["batch_pricing", "dual_pricing"]
        }

        updated_config = existing_config.set_default_pricer("treasury-v2.3")

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo), \
             patch('registry.api.pricing_router.get_tenant_service', return_value=mock_tenant_service):

            mock_tenant_service.get_tenant_by_id.return_value = tenant
            mock_repo.get_tenant_pricing_config.return_value = existing_config
            mock_repo.save_tenant_pricing_config.return_value = updated_config

            # Execute
            response = client.put(f"/registry/tenants/{tenant_id}/pricing-config", json=request_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == tenant_id
            assert data["default_pricer_id"] == "treasury-v2.3"

    def test_update_tenant_pricing_config_invalid_pricer(self, client, mock_repo, mock_tenant_service):
        """Test updating with invalid pricer ID."""
        # Setup
        tenant_id = str(uuid4())
        tenant = MagicMock()
        existing_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        request_data = {
            "default_pricer_id": "invalid-pricer-v1.0"
        }

        with patch('registry.api.pricing_router.get_pricing_repository', return_value=mock_repo), \
             patch('registry.api.pricing_router.get_tenant_service', return_value=mock_tenant_service):

            mock_tenant_service.get_tenant_by_id.return_value = tenant
            mock_repo.get_tenant_pricing_config.return_value = existing_config

            # Mock the pricer validation to raise ValueError
            mock_update = MagicMock()
            mock_update.set_default_pricer.side_effect = ValueError("Pricer invalid-pricer-v1.0 is not allowed")
            mock_config_instance = MagicMock()
            mock_config_instance.update_configuration.return_value = mock_update
            existing_config.update_configuration = mock_config_instance.update_configuration

            # Execute
            response = client.put(f"/registry/tenants/{tenant_id}/pricing-config", json=request_data)

            # Verify
            assert response.status_code == 400
            data = response.json()
            assert "not allowed" in data["detail"]