"""Integration tests for tenant export API endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from registry.api.rest import create_app
from registry.export_service import ExportStatus, TenantExportResult


@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    app = create_app(
        consul_host="localhost", consul_port=8500, kafka_bootstrap_servers=["localhost:9092"]
    )
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_export_result():
    """Sample export result for testing."""
    return TenantExportResult(
        export_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        status=ExportStatus.COMPLETED,
        file_path="/tmp/export_file.json",
        file_size_bytes=1024,
        records_exported=100,
        models_exported=["pricing.quotes", "reference_data.instruments"],
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


class TestExportEndpoints:
    """Test export API endpoints."""

    def test_export_tenant_data_success(self, test_client, sample_export_result):
        """Test successful tenant data export request."""
        tenant_id = str(uuid.uuid4())
        request_data = {
            "format": "json",
            "compress": True,
            "encrypt": True,
            "include_deleted": False,
            "include_audit_fields": True,
            "reason": "Test export for integration testing",
        }

        with patch("registry.api.rest.TenantExportService") as mock_service_class:
            # Mock the service instance
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Mock the export method
            mock_service.export_tenant_data.return_value = sample_export_result

            # Mock the dependency
            with patch("registry.api.rest.get_export_service") as mock_dependency:
                mock_dependency.return_value = mock_service

                response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

                assert response.status_code == 200

                data = response.json()
                assert data["export_id"] == sample_export_result.export_id
                assert data["tenant_id"] == sample_export_result.tenant_id
                assert data["status"] == sample_export_result.status
                assert "created_at" in data

    def test_export_tenant_data_invalid_format(self, test_client):
        """Test export with invalid format."""
        tenant_id = str(uuid.uuid4())
        request_data = {
            "format": "xml",  # Invalid format
            "reason": "Test with invalid format",
        }

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_dependency.return_value = AsyncMock()

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            assert response.status_code == 400
            assert "Invalid format" in response.json()["detail"]

    def test_export_tenant_data_missing_reason(self, test_client):
        """Test export without required reason."""
        tenant_id = str(uuid.uuid4())
        request_data = {
            "format": "json"
            # Missing required reason field
        }

        response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_export_tenant_data_short_reason(self, test_client):
        """Test export with reason that's too short."""
        tenant_id = str(uuid.uuid4())
        request_data = {
            "format": "json",
            "reason": "short",  # Too short (less than 10 chars)
        }

        response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_export_tenant_data_service_error(self, test_client):
        """Test export when service raises error."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": "json", "reason": "Test service error handling"}

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.export_tenant_data.side_effect = Exception("Service error")
            mock_dependency.return_value = mock_service

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            assert response.status_code == 500

    def test_get_export_status_success(self, test_client, sample_export_result):
        """Test successful export status retrieval."""
        export_id = sample_export_result.export_id

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.get_export_result.return_value = sample_export_result
            mock_dependency.return_value = mock_service

            response = test_client.get(f"/api/v1/export/status/{export_id}")

            assert response.status_code == 200

            data = response.json()
            assert data["export_id"] == sample_export_result.export_id
            assert data["tenant_id"] == sample_export_result.tenant_id
            assert data["status"] == sample_export_result.status
            assert data["file_path"] == sample_export_result.file_path
            assert data["file_size_bytes"] == sample_export_result.file_size_bytes
            assert data["records_exported"] == sample_export_result.records_exported
            assert data["models_exported"] == sample_export_result.models_exported

    def test_get_export_status_not_found(self, test_client):
        """Test export status retrieval for non-existent export."""
        export_id = str(uuid.uuid4())

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.get_export_result.return_value = None  # Not found
            mock_dependency.return_value = mock_service

            response = test_client.get(f"/api/v1/export/status/{export_id}")

            assert response.status_code == 404

    def test_get_export_status_service_error(self, test_client):
        """Test export status retrieval when service raises error."""
        export_id = str(uuid.uuid4())

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.get_export_result.side_effect = Exception("Service error")
            mock_dependency.return_value = mock_service

            response = test_client.get(f"/api/v1/export/status/{export_id}")

            assert response.status_code == 500


class TestExportAPIValidation:
    """Test API request validation."""

    @pytest.mark.parametrize("format_value", ["json", "csv", "jsonl"])
    def test_valid_formats(self, test_client, format_value):
        """Test all valid export formats."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": format_value, "reason": "Test valid format validation"}

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.export_tenant_data.return_value = TenantExportResult(
                export_id=str(uuid.uuid4()), tenant_id=tenant_id, status=ExportStatus.IN_PROGRESS
            )
            mock_dependency.return_value = mock_service

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            # Should not fail validation
            assert response.status_code == 200

    @pytest.mark.parametrize("invalid_format", ["xml", "yaml", "binary", ""])
    def test_invalid_formats(self, test_client, invalid_format):
        """Test invalid export formats."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": invalid_format, "reason": "Test invalid format validation"}

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_dependency.return_value = AsyncMock()

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            assert response.status_code == 400

    def test_boolean_field_validation(self, test_client):
        """Test boolean field validation."""
        tenant_id = str(uuid.uuid4())
        request_data = {
            "format": "json",
            "compress": "true",  # String instead of boolean
            "encrypt": 1,  # Number instead of boolean
            "reason": "Test boolean validation",
        }

        # FastAPI should coerce these to booleans
        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.export_tenant_data.return_value = TenantExportResult(
                export_id=str(uuid.uuid4()), tenant_id=tenant_id, status=ExportStatus.IN_PROGRESS
            )
            mock_dependency.return_value = mock_service

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            assert response.status_code == 200


class TestExportDependencyInjection:
    """Test dependency injection for export service."""

    @patch("registry.api.rest.TenantExportService")
    def test_export_service_dependency(self, mock_service_class, test_client):
        """Test that export service dependency is properly injected."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": "json", "reason": "Test dependency injection"}

        # Mock the service
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Mock initialization and methods
        mock_service.initialize = AsyncMock()
        mock_service.close = AsyncMock()
        mock_service.export_tenant_data.return_value = TenantExportResult(
            export_id=str(uuid.uuid4()), tenant_id=tenant_id, status=ExportStatus.IN_PROGRESS
        )

        test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)
        response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

        # Service should have been created and initialized
        mock_service_class.assert_called_once()
        mock_service.initialize.assert_called_once()


class TestExportResponseFormats:
    """Test API response formats."""

    def test_export_response_format(self, test_client, sample_export_result):
        """Test export response contains all required fields."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": "json", "reason": "Test response format"}

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.export_tenant_data.return_value = sample_export_result
            mock_dependency.return_value = mock_service

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            assert response.status_code == 200

            data = response.json()
            required_fields = ["export_id", "status", "tenant_id", "created_at"]
            for field in required_fields:
                assert field in data
                assert data[field] is not None

    def test_status_response_format(self, test_client, sample_export_result):
        """Test status response contains all required fields."""
        export_id = sample_export_result.export_id

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.get_export_result.return_value = sample_export_result
            mock_dependency.return_value = mock_service

            response = test_client.get(f"/api/v1/export/status/{export_id}")

            assert response.status_code == 200

            data = response.json()
            expected_fields = [
                "export_id",
                "tenant_id",
                "status",
                "file_path",
                "file_size_bytes",
                "records_exported",
                "models_exported",
                "created_at",
                "completed_at",
            ]
            for field in expected_fields:
                assert field in data

    def test_error_response_format(self, test_client):
        """Test error responses have consistent format."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": "invalid_format", "reason": "Test error response format"}

        response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

        assert response.status_code == 400
        assert "detail" in response.json()


class TestExportEndpointSecurity:
    """Test security aspects of export endpoints."""

    def test_reason_minimum_length_validation(self, test_client):
        """Test that reason field has minimum length validation."""
        tenant_id = str(uuid.uuid4())

        # Reason too short
        request_data = {
            "format": "json",
            "reason": "short",  # Only 5 characters
        }

        response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

        assert response.status_code == 422

        # Reason long enough
        request_data["reason"] = "Valid reason for testing export functionality"

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.export_tenant_data.return_value = TenantExportResult(
                export_id=str(uuid.uuid4()), tenant_id=tenant_id, status=ExportStatus.IN_PROGRESS
            )
            mock_dependency.return_value = mock_service

            response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)

            assert response.status_code == 200

    def test_tenant_id_validation(self, test_client):
        """Test tenant ID format validation."""
        request_data = {"format": "json", "reason": "Test tenant ID validation"}

        # Valid UUID format should work
        valid_tenant_id = str(uuid.uuid4())
        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()
            mock_service.export_tenant_data.return_value = TenantExportResult(
                export_id=str(uuid.uuid4()),
                tenant_id=valid_tenant_id,
                status=ExportStatus.IN_PROGRESS,
            )
            mock_dependency.return_value = mock_service

            response = test_client.post(
                f"/api/v1/export/tenant/{valid_tenant_id}", json=request_data
            )

            assert response.status_code == 200


class TestConcurrentExports:
    """Test handling of concurrent export requests."""

    def test_multiple_concurrent_exports(self, test_client):
        """Test that multiple exports can be initiated concurrently."""
        tenant_id = str(uuid.uuid4())
        request_data = {"format": "json", "reason": "Test concurrent export requests"}

        results = []

        with patch("registry.api.rest.get_export_service") as mock_dependency:
            mock_service = AsyncMock()

            # Return different export IDs for each request
            def side_effect(*args, **kwargs):
                return TenantExportResult(
                    export_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    status=ExportStatus.IN_PROGRESS,
                )

            mock_service.export_tenant_data.side_effect = side_effect
            mock_dependency.return_value = mock_service

            # Make multiple concurrent requests
            for i in range(3):
                response = test_client.post(f"/api/v1/export/tenant/{tenant_id}", json=request_data)
                assert response.status_code == 200
                results.append(response.json())

        # Each request should get a unique export ID
        export_ids = [result["export_id"] for result in results]
        assert len(set(export_ids)) == 3  # All unique
