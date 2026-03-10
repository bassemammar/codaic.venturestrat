"""
Unit tests for the health service.

Tests the health service independently of Kong Gateway.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient

# Add health-service to path for importing
health_service_path = Path(__file__).parent.parent.parent / "health-service"
sys.path.insert(0, str(health_service_path))

from main import app


@pytest.mark.unit
class TestHealthService:
    """Test suite for the health service."""

    @pytest.fixture
    def client(self):
        """FastAPI test client for health service."""
        return TestClient(app)

    def test_health_endpoint_response_format(self, client):
        """Test health endpoint returns correct format."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should have both required fields
        assert "status" in data
        assert "timestamp" in data

        # Status should be "healthy"
        assert data["status"] == "healthy"

        # Timestamp should be in ISO format with Z suffix
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        assert len(timestamp) >= 20  # Basic length check

        # Should be parseable as datetime
        # Remove Z and parse
        import dateutil.parser

        parsed_timestamp = dateutil.parser.parse(timestamp)
        assert isinstance(parsed_timestamp, datetime)

    def test_health_endpoint_timestamp_is_recent(self, client):
        """Test health endpoint returns recent timestamp."""
        before = datetime.now()
        response = client.get("/health")
        after = datetime.now()

        assert response.status_code == 200
        data = response.json()

        import dateutil.parser

        timestamp_str = data["timestamp"]
        # Parse timestamp (remove Z and add timezone info)
        parsed_timestamp = dateutil.parser.parse(timestamp_str)

        # Convert to naive datetime for comparison
        if parsed_timestamp.tzinfo is not None:
            # Convert to naive UTC datetime
            parsed_timestamp = parsed_timestamp.replace(tzinfo=None)

        # Should be between before and after (allowing some margin)
        time_diff_before = abs((parsed_timestamp - before).total_seconds())
        time_diff_after = abs((after - parsed_timestamp).total_seconds())

        # Should be within 2 seconds of the request time
        assert time_diff_before <= 2.0
        assert time_diff_after <= 2.0

    def test_root_endpoint_same_as_health(self, client):
        """Test root endpoint returns same as health endpoint."""
        health_response = client.get("/health")
        root_response = client.get("/")

        assert health_response.status_code == 200
        assert root_response.status_code == 200

        health_data = health_response.json()
        root_data = root_response.json()

        # Both should have same structure (timestamps will differ slightly)
        assert health_data["status"] == root_data["status"]
        assert "timestamp" in health_data
        assert "timestamp" in root_data

    def test_health_endpoint_content_type(self, client):
        """Test health endpoint returns JSON."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_no_authentication_required(self, client):
        """Test health endpoint is accessible without authentication."""
        # Health endpoint should work without any headers
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_multiple_requests_get_different_timestamps(self, client):
        """Test multiple health requests get different timestamps."""
        import time

        response1 = client.get("/health")
        time.sleep(0.1)  # Small delay to ensure different timestamps
        response2 = client.get("/health")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Status should be the same
        assert data1["status"] == data2["status"] == "healthy"

        # Timestamps should be different
        assert data1["timestamp"] != data2["timestamp"]

    def test_health_response_pydantic_model(self, client):
        """Test response matches Pydantic model structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should only have the two expected fields
        expected_fields = {"status", "timestamp"}
        actual_fields = set(data.keys())
        assert actual_fields == expected_fields

        # Field types should be strings
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
