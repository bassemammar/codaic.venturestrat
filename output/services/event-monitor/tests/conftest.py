"""Pytest configuration and fixtures for Event Monitor."""

import pytest
from fastapi.testclient import TestClient

from event_monitor.main import app


@pytest.fixture
def client() -> TestClient:
  """Create a test client for the FastAPI application."""
  return TestClient(app)
