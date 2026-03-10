"""Unit tests for health monitoring endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from registry.api.pricing_router import (
    pricing_router,
    get_health_summary,
    get_health_metrics,
    get_pricer_health_status,
    get_circuit_breaker_statuses,
)
from registry.models.pricer_registry import PricerRegistry, PricerStatus


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(pricing_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_pricers():
    """Mock list of pricers for testing."""
    return [
        PricerRegistry(
            pricer_id="quantlib-v1.18",
            name="QuantLib",
            version="1.18.0",
            description="QuantLib pricing engine",
            health_check_url="http://quantlib:8088/health",
            pricing_url="http://quantlib:8088/api/v1",
            status=PricerStatus.HEALTHY.value,
            last_health_check=datetime.now(timezone.utc),
            health_check_failures=0,
            batch_supported=True,
            max_batch_size=10000
        ),
        PricerRegistry(
            pricer_id="treasury-v2.3",
            name="Treasury",
            version="2.3.0",
            description="Treasury pricing engine",
            health_check_url="http://treasury:8101/health",
            pricing_url="http://treasury:8101/api/v1",
            status=PricerStatus.UNHEALTHY.value,
            last_health_check=datetime.now(timezone.utc),
            health_check_failures=3,
            batch_supported=True,
            max_batch_size=5000
        ),
        PricerRegistry(
            pricer_id="disabled-pricer-v1.0",
            name="Disabled Pricer",
            version="1.0.0",
            description="Disabled for maintenance",
            health_check_url="http://disabled:8080/health",
            pricing_url="http://disabled:8080/api/v1",
            status=PricerStatus.DISABLED.value,
            last_health_check=None,
            health_check_failures=0,
            batch_supported=False,
            max_batch_size=None
        )
    ]


class TestHealthSummaryEndpoint:
    """Test health summary endpoint."""

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_health_summary_basic(self, mock_repo_dep, client, mock_pricers):
        """Test basic health summary without details."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = mock_pricers
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["total_pricers"] == 3
        assert data["healthy_pricers"] == 1
        assert data["unhealthy_pricers"] == 1
        assert data["disabled_pricers"] == 1
        assert data["unknown_pricers"] == 0
        assert data["health_ratio"] == 1/3  # 1 healthy out of 3 total
        assert data["monitoring_enabled"] is False
        assert data["pricers"] == []  # No details by default

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_health_summary_with_details(self, mock_repo_dep, client, mock_pricers):
        """Test health summary with individual pricer details."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = mock_pricers
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/summary?include_details=true")

        assert response.status_code == 200
        data = response.json()

        assert data["total_pricers"] == 3
        assert len(data["pricers"]) == 3

        # Check first pricer details
        quantlib_pricer = next(p for p in data["pricers"] if p["pricer_id"] == "quantlib-v1.18")
        assert quantlib_pricer["name"] == "QuantLib"
        assert quantlib_pricer["status"] == "healthy"
        assert quantlib_pricer["health_check_failures"] == 0
        assert quantlib_pricer["last_health_check"] is not None

        # Check unhealthy pricer
        treasury_pricer = next(p for p in data["pricers"] if p["pricer_id"] == "treasury-v2.3")
        assert treasury_pricer["status"] == "unhealthy"
        assert treasury_pricer["health_check_failures"] == 3

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_health_summary_empty_list(self, mock_repo_dep, client):
        """Test health summary with no pricers."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = []
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["total_pricers"] == 0
        assert data["healthy_pricers"] == 0
        assert data["unhealthy_pricers"] == 0
        assert data["health_ratio"] == 1.0  # Default when no pricers

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_health_summary_database_error(self, mock_repo_dep, client):
        """Test health summary with database error."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.side_effect = Exception("Database connection failed")
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/summary")

        assert response.status_code == 500
        assert "Failed to get health summary" in response.json()["detail"]


class TestHealthMetricsEndpoint:
    """Test health metrics endpoint."""

    def test_health_metrics_default(self, client):
        """Test health metrics endpoint with default values."""
        response = client.get("/registry/health/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check monitoring configuration
        config = data["monitoring_config"]
        assert config["check_interval_seconds"] == 30
        assert config["timeout_seconds"] == 10
        assert config["failure_threshold"] == 3
        assert config["recovery_threshold"] == 2
        assert config["retry_backoff_seconds"] == 60
        assert config["max_concurrent_checks"] == 10

        # Check metrics
        metrics = data["metrics"]
        assert metrics["total_checks"] == 0
        assert metrics["successful_checks"] == 0
        assert metrics["failed_checks"] == 0
        assert metrics["success_rate"] == 1.0
        assert metrics["is_running"] is False

        # Check circuit breaker states
        assert data["circuit_breaker_states"] == {}


class TestPricerHealthStatusEndpoint:
    """Test individual pricer health status endpoint."""

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_get_pricer_health_status_found(self, mock_repo_dep, client, mock_pricers):
        """Test getting health status for existing pricer."""
        mock_repo = AsyncMock()
        mock_repo.get_pricer.return_value = mock_pricers[0]
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/pricers/quantlib-v1.18")

        assert response.status_code == 200
        data = response.json()

        assert data["pricer_id"] == "quantlib-v1.18"
        assert data["name"] == "QuantLib"
        assert data["status"] == "healthy"
        assert data["health_check_failures"] == 0
        assert data["last_health_check"] is not None

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_get_pricer_health_status_not_found(self, mock_repo_dep, client):
        """Test getting health status for non-existent pricer."""
        mock_repo = AsyncMock()
        mock_repo.get_pricer.return_value = None
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/pricers/nonexistent-pricer")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_get_pricer_health_status_database_error(self, mock_repo_dep, client):
        """Test getting health status with database error."""
        mock_repo = AsyncMock()
        mock_repo.get_pricer.side_effect = Exception("Database error")
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/pricers/quantlib-v1.18")

        assert response.status_code == 500
        assert "Failed to get pricer health status" in response.json()["detail"]


class TestCircuitBreakerStatusEndpoint:
    """Test circuit breaker status endpoint."""

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_get_circuit_breaker_statuses(self, mock_repo_dep, client, mock_pricers):
        """Test getting circuit breaker statuses for all pricers."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = mock_pricers
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/circuit-breakers")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3

        # Check healthy pricer circuit breaker
        quantlib_cb = next(cb for cb in data if cb["pricer_id"] == "quantlib-v1.18")
        assert quantlib_cb["state"] == "closed"
        assert quantlib_cb["failure_count"] == 0

        # Check unhealthy pricer circuit breaker
        treasury_cb = next(cb for cb in data if cb["pricer_id"] == "treasury-v2.3")
        assert treasury_cb["state"] == "open"
        assert treasury_cb["failure_count"] == 3

        # Check disabled pricer circuit breaker
        disabled_cb = next(cb for cb in data if cb["pricer_id"] == "disabled-pricer-v1.0")
        assert disabled_cb["state"] == "unknown"
        assert disabled_cb["failure_count"] == 0

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_circuit_breaker_statuses_empty(self, mock_repo_dep, client):
        """Test circuit breaker statuses with no pricers."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = []
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/circuit-breakers")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_circuit_breaker_statuses_database_error(self, mock_repo_dep, client):
        """Test circuit breaker statuses with database error."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.side_effect = Exception("Database connection lost")
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        response = client.get("/registry/health/circuit-breakers")

        assert response.status_code == 500
        assert "Failed to get circuit breaker statuses" in response.json()["detail"]


class TestHealthEndpointIntegration:
    """Integration tests for health endpoints."""

    @patch('registry.api.pricing_router.get_pricing_repository')
    def test_health_endpoints_consistency(self, mock_repo_dep, client, mock_pricers):
        """Test that all health endpoints return consistent data."""
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = mock_pricers
        mock_repo.get_pricer.return_value = mock_pricers[0]
        mock_repo_dep.return_value.__aenter__.return_value = mock_repo
        mock_repo_dep.return_value.__aexit__.return_value = None

        # Get health summary
        summary_response = client.get("/registry/health/summary?include_details=true")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()

        # Get individual pricer status
        pricer_response = client.get("/registry/health/pricers/quantlib-v1.18")
        assert pricer_response.status_code == 200
        pricer_data = pricer_response.json()

        # Get circuit breaker statuses
        cb_response = client.get("/registry/health/circuit-breakers")
        assert cb_response.status_code == 200
        cb_data = cb_response.json()

        # Verify consistency
        quantlib_summary = next(p for p in summary_data["pricers"] if p["pricer_id"] == "quantlib-v1.18")
        assert quantlib_summary["status"] == pricer_data["status"]
        assert quantlib_summary["health_check_failures"] == pricer_data["health_check_failures"]

        quantlib_cb = next(cb for cb in cb_data if cb["pricer_id"] == "quantlib-v1.18")
        expected_state = "closed" if pricer_data["status"] == "healthy" else "open"
        assert quantlib_cb["state"] == expected_state

    @pytest.mark.asyncio
    async def test_health_endpoints_async_context(self, mock_pricers):
        """Test health endpoints work correctly in async context."""
        # This test verifies the async dependencies work correctly

        # Mock repository dependency
        mock_repo = AsyncMock()
        mock_repo.list_pricers.return_value = mock_pricers

        # Test health summary function directly
        summary = await get_health_summary(repo=mock_repo, include_details=True)

        assert summary.total_pricers == 3
        assert summary.healthy_pricers == 1
        assert summary.unhealthy_pricers == 1
        assert summary.disabled_pricers == 1
        assert len(summary.pricers) == 3

        # Test metrics function
        metrics = await get_health_metrics()

        assert metrics.monitoring_config["check_interval_seconds"] == 30
        assert metrics.metrics["total_checks"] == 0

        # Test individual pricer status
        mock_repo.get_pricer.return_value = mock_pricers[0]
        pricer_status = await get_pricer_health_status("quantlib-v1.18", repo=mock_repo)

        assert pricer_status.pricer_id == "quantlib-v1.18"
        assert pricer_status.status == "healthy"

        # Test circuit breaker statuses
        cb_statuses = await get_circuit_breaker_statuses(repo=mock_repo)

        assert len(cb_statuses) == 3
        assert any(cb.pricer_id == "quantlib-v1.18" and cb.state == "closed" for cb in cb_statuses)
        assert any(cb.pricer_id == "treasury-v2.3" and cb.state == "open" for cb in cb_statuses)