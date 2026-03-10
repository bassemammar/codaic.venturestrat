"""Tests for EventPublisher - TDD approach.

Tests for Kafka event publishing for service lifecycle events.
"""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from registry.events import (
    EventPublisher,
    EventType,
    ServiceDeregisteredEvent,
    ServiceEvent,
    ServiceHealthChangedEvent,
    ServiceRegisteredEvent,
    TenantCreatedEvent,
    TenantDeletedEvent,
    TenantEventPublisher,
    TenantPurgedEvent,
)
from registry.health import HealthTransition
from registry.models import HealthStatus, Protocol, ServiceRegistration


@pytest.fixture
def mock_producer():
    """Create mock Kafka producer."""
    producer = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.send_and_wait = AsyncMock()
    return producer


@pytest.fixture
def event_publisher(mock_producer):
    """Create EventPublisher with mocked producer."""
    publisher = EventPublisher(
        bootstrap_servers="localhost:9092",
        topic="platform.services.lifecycle",
    )
    # Directly inject mock producer
    publisher._producer = mock_producer
    return publisher


@pytest.fixture
def sample_registration():
    """Create sample registration."""
    return ServiceRegistration(
        name="test-service",
        version="1.0.0",
        instance_id="test-service-abc123",
        address="10.0.1.50",
        port=8080,
        protocol=Protocol.HTTP,
        tags=["production"],
        metadata={"team": "platform"},
    )


class TestEventTypes:
    """Tests for event type definitions."""

    def test_event_type_values(self):
        """Event types have correct values."""
        assert EventType.REGISTERED.value == "service.registered"
        assert EventType.DEREGISTERED.value == "service.deregistered"
        assert EventType.HEALTH_CHANGED.value == "service.health_changed"


class TestServiceEvent:
    """Tests for base ServiceEvent model."""

    def test_create_event(self):
        """Create base service event."""
        event = ServiceEvent(
            event_type=EventType.REGISTERED,
            service_name="test-service",
            instance_id="test-123",
            version="1.0.0",
        )

        assert event.event_type == EventType.REGISTERED
        assert event.timestamp is not None

    def test_event_to_json(self):
        """Event serializes to JSON."""
        event = ServiceEvent(
            event_type=EventType.REGISTERED,
            service_name="test-service",
            instance_id="test-123",
            version="1.0.0",
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["event_type"] == "service.registered"
        assert data["service_name"] == "test-service"
        assert "timestamp" in data


class TestServiceRegisteredEvent:
    """Tests for service registered event."""

    def test_create_from_registration(self, sample_registration):
        """Create event from ServiceRegistration."""
        event = ServiceRegisteredEvent.from_registration(sample_registration)

        assert event.event_type == EventType.REGISTERED
        assert event.service_name == "test-service"
        assert event.version == "1.0.0"
        assert event.address == "10.0.1.50"
        assert event.port == 8080
        assert "production" in event.tags

    def test_event_json_schema(self, sample_registration):
        """Event JSON matches expected schema."""
        event = ServiceRegisteredEvent.from_registration(sample_registration)
        data = json.loads(event.to_json())

        # Required fields
        assert "event_type" in data
        assert "timestamp" in data
        assert "service_name" in data
        assert "instance_id" in data
        assert "version" in data
        assert "address" in data
        assert "port" in data


class TestServiceDeregisteredEvent:
    """Tests for service deregistered event."""

    def test_create_event(self):
        """Create deregistered event."""
        event = ServiceDeregisteredEvent(
            service_name="test-service",
            instance_id="test-123",
            version="1.0.0",
            reason="graceful_shutdown",
        )

        assert event.event_type == EventType.DEREGISTERED
        assert event.reason == "graceful_shutdown"

    def test_create_with_timeout_reason(self):
        """Create event with health check timeout reason."""
        event = ServiceDeregisteredEvent(
            service_name="test-service",
            instance_id="test-123",
            version="1.0.0",
            reason="health_check_timeout",
        )

        assert event.reason == "health_check_timeout"


class TestServiceHealthChangedEvent:
    """Tests for health changed event."""

    def test_create_from_transition(self):
        """Create event from HealthTransition."""
        transition = HealthTransition(
            instance_id="test-123",
            service_name="test-service",
            previous_status=HealthStatus.HEALTHY,
            new_status=HealthStatus.CRITICAL,
            check_name="http-check",
            check_output="Connection refused",
        )

        event = ServiceHealthChangedEvent.from_transition(transition, version="1.0.0")

        assert event.event_type == EventType.HEALTH_CHANGED
        assert event.previous_status == "healthy"
        assert event.new_status == "critical"
        assert event.check_name == "http-check"


class TestEventPublisherConnection:
    """Tests for EventPublisher connection management."""

    @pytest.mark.asyncio
    async def test_start_producer(self, event_publisher, mock_producer):
        """Start connects to Kafka."""
        await event_publisher.start()
        mock_producer.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_producer(self, event_publisher, mock_producer):
        """Stop disconnects from Kafka."""
        await event_publisher.stop()
        mock_producer.stop.assert_called_once()


class TestEventPublisherPublishing:
    """Tests for event publishing."""

    @pytest.mark.asyncio
    async def test_publish_registered_event(
        self, event_publisher, mock_producer, sample_registration
    ):
        """Publish service registered event."""
        await event_publisher.publish_registered(sample_registration)

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args

        assert call_args[0][0] == "platform.services.lifecycle"
        # Message value should be JSON
        message = call_args[1].get("value") or call_args[0][1]
        data = json.loads(message.decode() if isinstance(message, bytes) else message)
        assert data["event_type"] == "service.registered"

    @pytest.mark.asyncio
    async def test_publish_deregistered_event(self, event_publisher, mock_producer):
        """Publish service deregistered event."""
        await event_publisher.publish_deregistered(
            service_name="test-service",
            instance_id="test-123",
            version="1.0.0",
            reason="graceful_shutdown",
        )

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        message = call_args[1].get("value") or call_args[0][1]
        data = json.loads(message.decode() if isinstance(message, bytes) else message)
        assert data["event_type"] == "service.deregistered"
        assert data["reason"] == "graceful_shutdown"

    @pytest.mark.asyncio
    async def test_publish_health_changed_event(self, event_publisher, mock_producer):
        """Publish health changed event."""
        transition = HealthTransition(
            instance_id="test-123",
            service_name="test-service",
            previous_status=HealthStatus.HEALTHY,
            new_status=HealthStatus.CRITICAL,
            check_name="http-check",
        )

        await event_publisher.publish_health_changed(transition, version="1.0.0")

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        message = call_args[1].get("value") or call_args[0][1]
        data = json.loads(message.decode() if isinstance(message, bytes) else message)
        assert data["event_type"] == "service.health_changed"

    @pytest.mark.asyncio
    async def test_publish_with_key(self, event_publisher, mock_producer, sample_registration):
        """Events are keyed by service name for partitioning."""
        await event_publisher.publish_registered(sample_registration)

        call_args = mock_producer.send_and_wait.call_args
        key = call_args[1].get("key")
        assert key is not None
        key_str = key.decode() if isinstance(key, bytes) else key
        assert "test-service" in key_str


class TestEventPublisherErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_publish_failure_logged(
        self, event_publisher, mock_producer, sample_registration, caplog
    ):
        """Publish failure is logged but doesn't raise."""
        mock_producer.send_and_wait.side_effect = Exception("Kafka error")

        # Should not raise
        await event_publisher.publish_registered(sample_registration)

        assert "error" in caplog.text.lower() or "fail" in caplog.text.lower()


# =============================================================================
# Tenant Event Tests
# =============================================================================


class TestTenantDeletedEvent:
    """Tests for TenantDeletedEvent class."""

    def test_tenant_deleted_event_creation(self):
        """TenantDeletedEvent creates with correct fields."""
        event = TenantDeletedEvent(
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            deletion_reason="Test deletion",
            deleted_at="2026-01-05T10:00:00Z",
            purge_at="2026-02-04T10:00:00Z",
        )

        assert event.event_type == EventType.TENANT_DELETED
        assert event.tenant_id == "tenant-id"
        assert event.tenant_slug == "tenant-slug"
        assert event.tenant_name == "Test Tenant"
        assert event.deletion_reason == "Test deletion"
        assert event.deleted_at == "2026-01-05T10:00:00Z"
        assert event.purge_at == "2026-02-04T10:00:00Z"
        assert event.timestamp is not None

    def test_tenant_deleted_event_to_json(self):
        """TenantDeletedEvent serializes to JSON correctly."""
        timestamp = datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC)
        event = TenantDeletedEvent(
            timestamp=timestamp,
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            deletion_reason="Test deletion",
            deleted_at="2026-01-05T10:00:00Z",
            purge_at="2026-02-04T10:00:00Z",
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["event_type"] == "tenant.deleted"
        assert data["timestamp"] == "2026-01-05T10:00:00+00:00"
        assert data["tenant_id"] == "tenant-id"
        assert data["tenant_slug"] == "tenant-slug"
        assert data["tenant_name"] == "Test Tenant"
        assert data["deletion_reason"] == "Test deletion"
        assert data["deleted_at"] == "2026-01-05T10:00:00Z"
        assert data["purge_at"] == "2026-02-04T10:00:00Z"


class TestTenantPurgedEvent:
    """Tests for TenantPurgedEvent class."""

    def test_tenant_purged_event_creation(self):
        """TenantPurgedEvent creates with correct fields."""
        event = TenantPurgedEvent(
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            keycloak_org_id="org-12345",
            deleted_at="2026-01-05T10:00:00Z",
            purged_at="2026-02-04T10:00:00Z",
        )

        assert event.event_type == EventType.TENANT_PURGED
        assert event.tenant_id == "tenant-id"
        assert event.tenant_slug == "tenant-slug"
        assert event.tenant_name == "Test Tenant"
        assert event.keycloak_org_id == "org-12345"
        assert event.deleted_at == "2026-01-05T10:00:00Z"
        assert event.purged_at == "2026-02-04T10:00:00Z"
        assert event.timestamp is not None

    def test_tenant_purged_event_with_null_keycloak_org_id(self):
        """TenantPurgedEvent handles null Keycloak org ID correctly."""
        event = TenantPurgedEvent(
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            keycloak_org_id=None,
            deleted_at=None,
            purged_at="2026-02-04T10:00:00Z",
        )

        assert event.keycloak_org_id is None
        assert event.deleted_at is None

        # Should serialize correctly
        json_str = event.to_json()
        data = json.loads(json_str)
        assert data["keycloak_org_id"] is None
        assert data["deleted_at"] is None


class TestTenantEventPublisher:
    """Tests for TenantEventPublisher class."""

    def test_tenant_event_publisher_initialization(self):
        """TenantEventPublisher initializes correctly."""
        publisher = TenantEventPublisher()

        assert publisher.bootstrap_servers == "localhost:9092"
        assert publisher.topic == "platform.tenant.lifecycle"
        assert publisher._producer is None

    @pytest.mark.asyncio
    async def test_publish_tenant_deleted(self):
        """publish_tenant_deleted() publishes event correctly."""
        publisher = TenantEventPublisher()
        mock_producer = AsyncMock()
        publisher._producer = mock_producer

        await publisher.publish_tenant_deleted(
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            deletion_reason="Test deletion",
            deleted_at="2026-01-05T10:00:00Z",
            purge_at="2026-02-04T10:00:00Z",
        )

        # Verify producer was called with correct parameters
        mock_producer.send_and_wait.assert_called_once()

        call_args = mock_producer.send_and_wait.call_args
        assert call_args[0][0] == "platform.tenant.lifecycle"  # topic

        # Check key
        key = call_args[1]["key"]
        assert key == b"tenant.tenant-id"

        # Check value (should be JSON bytes)
        value = call_args[1]["value"]
        event_data = json.loads(value.decode("utf-8"))
        assert event_data["event_type"] == "tenant.deleted"
        assert event_data["tenant_id"] == "tenant-id"
        assert event_data["tenant_slug"] == "tenant-slug"

    @pytest.mark.asyncio
    async def test_publish_tenant_purged(self):
        """publish_tenant_purged() publishes event correctly."""
        publisher = TenantEventPublisher()
        mock_producer = AsyncMock()
        publisher._producer = mock_producer

        await publisher.publish_tenant_purged(
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            keycloak_org_id="org-12345",
            deleted_at="2026-01-05T10:00:00Z",
            purged_at="2026-02-04T10:00:00Z",
        )

        # Verify producer was called
        mock_producer.send_and_wait.assert_called_once()

        call_args = mock_producer.send_and_wait.call_args
        assert call_args[0][0] == "platform.tenant.lifecycle"

        # Check key
        key = call_args[1]["key"]
        assert key == b"tenant.tenant-id"

        # Check value
        value = call_args[1]["value"]
        event_data = json.loads(value.decode("utf-8"))
        assert event_data["event_type"] == "tenant.purged"
        assert event_data["tenant_id"] == "tenant-id"
        assert event_data["keycloak_org_id"] == "org-12345"

    @pytest.mark.asyncio
    async def test_publish_when_producer_not_started(self):
        """Publishing warns when producer is not started."""
        publisher = TenantEventPublisher()
        # No producer started

        # Should not raise, just log warning
        await publisher.publish_tenant_deleted(
            tenant_id="tenant-id",
            tenant_slug="tenant-slug",
            tenant_name="Test Tenant",
            deletion_reason="Test deletion",
            deleted_at="2026-01-05T10:00:00Z",
            purge_at="2026-02-04T10:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_publish_tenant_created_success(self):
        """publish_tenant_created publishes tenant creation event."""
        # Mock producer
        mock_producer = AsyncMock()

        publisher = TenantEventPublisher()
        publisher._producer = mock_producer

        await publisher.publish_tenant_created(
            tenant_id="tenant-12345",
            tenant_slug="test-tenant",
            tenant_name="Test Tenant",
            keycloak_org_id="org-67890",
            admin_email="admin@test.com",
            config={"theme": {"primary_color": "#0066cc"}},
            created_at="2026-01-05T10:00:00Z",
        )

        # Verify event was published
        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args

        # Check topic and key
        assert call_args[0][0] == "platform.tenant.lifecycle"  # topic
        assert call_args[1]["key"] == b"tenant.tenant-12345"

        # Check event content
        event_data = json.loads(call_args[1]["value"].decode("utf-8"))
        assert event_data["event_type"] == "tenant.created"
        assert event_data["tenant_id"] == "tenant-12345"
        assert event_data["tenant_slug"] == "test-tenant"
        assert event_data["tenant_name"] == "Test Tenant"
        assert event_data["keycloak_org_id"] == "org-67890"
        assert event_data["admin_email"] == "admin@test.com"
        assert event_data["config"] == {"theme": {"primary_color": "#0066cc"}}
        assert event_data["created_at"] == "2026-01-05T10:00:00Z"
        assert "timestamp" in event_data

    @pytest.mark.asyncio
    async def test_tenant_created_event_serialization(self):
        """TenantCreatedEvent serializes correctly to JSON."""
        event = TenantCreatedEvent(
            tenant_id="tenant-12345",
            tenant_slug="test-tenant",
            tenant_name="Test Tenant",
            keycloak_org_id="org-67890",
            admin_email="admin@test.com",
            config={"quotas": {"max_users": 100}},
            created_at="2026-01-05T10:00:00Z",
        )

        # Test JSON serialization
        json_str = event.to_json()
        event_data = json.loads(json_str)

        assert event_data["event_type"] == "tenant.created"
        assert event_data["tenant_id"] == "tenant-12345"
        assert event_data["tenant_slug"] == "test-tenant"
        assert event_data["tenant_name"] == "Test Tenant"
        assert event_data["keycloak_org_id"] == "org-67890"
        assert event_data["admin_email"] == "admin@test.com"
        assert event_data["config"] == {"quotas": {"max_users": 100}}
        assert event_data["created_at"] == "2026-01-05T10:00:00Z"

        # Test bytes serialization
        event_bytes = event.to_bytes()
        assert isinstance(event_bytes, bytes)
        assert json.loads(event_bytes.decode("utf-8"))["event_type"] == "tenant.created"

    @pytest.mark.asyncio
    async def test_publish_tenant_created_with_minimal_data(self):
        """publish_tenant_created works with minimal data."""
        mock_producer = AsyncMock()

        publisher = TenantEventPublisher()
        publisher._producer = mock_producer

        await publisher.publish_tenant_created(
            tenant_id="tenant-12345",
            tenant_slug="test-tenant",
            tenant_name="Test Tenant",
            keycloak_org_id=None,
            admin_email=None,
            config=None,
            created_at="2026-01-05T10:00:00Z",
        )

        # Verify event was published
        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args

        # Check event content handles None values
        event_data = json.loads(call_args[1]["value"].decode("utf-8"))
        assert event_data["event_type"] == "tenant.created"
        assert event_data["tenant_id"] == "tenant-12345"
        assert event_data["keycloak_org_id"] is None
        assert event_data["admin_email"] is None
        assert event_data["config"] == {}  # Empty dict for None config
