"""Tests for TenantService event emission functionality.

This module tests the new structured event emission added for task 18.3,
including all tenant lifecycle events: created, suspended, resumed, deleted, and updated.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from registry.models import Tenant
from registry.tenant_service import TenantService
from venturestrat.tenancy.events import (
    TenantCreatedEvent,
    TenantDeletedEvent,
    TenantResumedEvent,
    TenantSuspendedEvent,
    TenantUpdatedEvent,
)
from venturestrat.tenancy.events import TenantStatus as TenantEventStatus


class MockAsyncContextManager:
    """Helper class for mocking async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class TestTenantServiceCreateEventEmission:
    """Tests for tenant creation event emission."""

    @pytest.fixture
    def mock_pool(self):
        """Mock database connection pool."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))
        return pool, conn

    @pytest.mark.asyncio
    async def test_create_tenant_emits_structured_event(self, mock_pool):
        """Test that create_tenant emits properly structured TenantCreatedEvent."""
        pool, conn = mock_pool

        # Mock successful tenant creation
        conn.fetchrow.return_value = None  # No existing tenant with slug
        conn.execute.return_value = None

        service = TenantService()
        service._pool = pool

        # Mock the event publisher to capture events
        service._event_publisher.publish = AsyncMock()

        # Mock Keycloak operations
        with patch.object(service, "_create_keycloak_organization") as mock_keycloak, patch.object(
            service, "_invite_admin_user"
        ):
        ) as mock_invite:
            mock_keycloak.return_value = "org-test-123"

            # Create tenant with full parameters
            tenant = await service.create_tenant(
                slug="test-tenant",
                name="Test Tenant",
                config={"quotas": {"max_users": 100}},
                admin_email="admin@test.com",
            )

            # Verify structured event was published
            service._event_publisher.publish.assert_called_once()

            # Get the event and topic from the call
            call_args = service._event_publisher.publish.call_args
            published_event = call_args[0][0]
            topic = call_args[1]["topic"]

            # Verify event type and structure
            assert isinstance(published_event, TenantCreatedEvent)
            assert published_event.event_type == "tenant.tenant.created"
            assert topic == "tenant.lifecycle"

            # Verify event data
            assert published_event.data.tenant_id == tenant.id
            assert published_event.data.tenant_slug == "test-tenant"
            assert published_event.data.tenant_name == "Test Tenant"
            assert published_event.data.status == TenantEventStatus.ACTIVE
            assert published_event.data.config == {"quotas": {"max_users": 100}}
            assert published_event.data.keycloak_org_id == "org-test-123"
            assert published_event.data.admin_email == "admin@test.com"
            assert isinstance(published_event.data.created_at, datetime)

            # Verify envelope fields
            assert published_event.source_service == "registry-service"
            assert published_event.tenant_id is None  # System context
            assert published_event.correlation_id is not None
            assert published_event.metadata["subject_tenant_id"] == tenant.id
            assert published_event.metadata["subject_tenant_slug"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_create_tenant_event_emission_failure_graceful(self, mock_pool):
        """Test that event emission failure doesn't break tenant creation."""
        pool, conn = mock_pool

        # Mock successful tenant creation
        conn.fetchrow.return_value = None
        conn.execute.return_value = None

        service = TenantService()
        service._pool = pool

        # Mock event publisher failure
        service._event_publisher.publish = AsyncMock(side_effect=Exception("Kafka unavailable"))

        # Mock Keycloak operations
        with patch.object(service, "_create_keycloak_organization") as mock_keycloak, patch.object(
            service, "_invite_admin_user"
        ):
        ) as mock_invite:
            mock_keycloak.return_value = "org-test-123"

            # Create tenant should succeed despite event failure
            tenant = await service.create_tenant(slug="test-tenant", name="Test Tenant")

            # Verify tenant was created successfully
            assert isinstance(tenant, Tenant)
            assert tenant.slug == "test-tenant"
            assert tenant.name == "Test Tenant"

            # Verify event publisher was called but failed
            service._event_publisher.publish.assert_called_once()


class TestTenantServiceSuspendEventEmission:
    """Tests for tenant suspension event emission."""

    @pytest.fixture
    def mock_pool_with_tenant(self):
        """Mock database pool with existing tenant."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))

        # Mock active tenant data
        tenant_data = {
            "id": "tenant-123",
            "slug": "test-tenant",
            "name": "Test Tenant",
            "status": "active",
            "config": {"quotas": {"max_users": 50}},
            "keycloak_org_id": "org-123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
        }
        conn.fetchrow.return_value = tenant_data

        return pool, conn

    @pytest.mark.asyncio
    async def test_suspend_tenant_emits_structured_event(self, mock_pool_with_tenant):
        """Test that suspend_tenant emits properly structured TenantSuspendedEvent."""
        pool, conn = mock_pool_with_tenant

        service = TenantService()
        service._pool = pool
        service._event_publisher.publish = AsyncMock()

        # Execute suspension
        reason = "Payment overdue - invoice #12345"
        await service.suspend_tenant("tenant-123", reason)

        # Verify structured event was published
        service._event_publisher.publish.assert_called_once()

        # Get the event from the call
        call_args = service._event_publisher.publish.call_args
        published_event = call_args[0][0]
        topic = call_args[1]["topic"]

        # Verify event type and structure
        assert isinstance(published_event, TenantSuspendedEvent)
        assert published_event.event_type == "tenant.tenant.suspended"
        assert topic == "tenant.lifecycle"

        # Verify event data
        assert published_event.data.tenant_id == "tenant-123"
        assert published_event.data.tenant_slug == "test-tenant"
        assert published_event.data.tenant_name == "Test Tenant"
        assert published_event.data.reason == reason
        assert published_event.data.previous_status == TenantEventStatus.ACTIVE
        assert isinstance(published_event.data.suspended_at, datetime)

        # Verify envelope fields
        assert published_event.source_service == "registry-service"
        assert published_event.metadata["subject_tenant_id"] == "tenant-123"
        assert published_event.metadata["suspension_reason"] == reason

    @pytest.mark.asyncio
    async def test_suspend_tenant_event_emission_failure_graceful(self, mock_pool_with_tenant):
        """Test that event emission failure doesn't break tenant suspension."""
        pool, conn = mock_pool_with_tenant

        service = TenantService()
        service._pool = pool

        # Mock event publisher failure
        service._event_publisher.publish = AsyncMock(
            side_effect=Exception("Event publishing failed")
        )

        # Execute suspension should succeed despite event failure
        result = await service.suspend_tenant("tenant-123", "Payment overdue")

        # Verify suspension was completed
        assert result is not None
        assert result.status == "suspended"

        # Verify event publisher was called but failed
        service._event_publisher.publish.assert_called_once()


class TestTenantServiceResumeEventEmission:
    """Tests for tenant resume event emission."""

    @pytest.fixture
    def mock_pool_with_suspended_tenant(self):
        """Mock database pool with suspended tenant."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))

        # Mock suspended tenant data
        tenant_data = {
            "id": "tenant-123",
            "slug": "test-tenant",
            "name": "Test Tenant",
            "status": "suspended",
            "config": {
                "quotas": {"max_users": 50},
                "suspension_reason": "Payment overdue",
                "suspended_at": "2026-01-05T10:00:00+00:00",
            },
            "keycloak_org_id": "org-123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
        }
        conn.fetchrow.return_value = tenant_data

        return pool, conn

    @pytest.mark.asyncio
    async def test_resume_tenant_emits_structured_event(self, mock_pool_with_suspended_tenant):
        """Test that resume_tenant emits properly structured TenantResumedEvent."""
        pool, conn = mock_pool_with_suspended_tenant

        service = TenantService()
        service._pool = pool
        service._event_publisher.publish = AsyncMock()

        # Execute resumption
        await service.resume_tenant("tenant-123")

        # Verify structured event was published
        service._event_publisher.publish.assert_called_once()

        # Get the event from the call
        call_args = service._event_publisher.publish.call_args
        published_event = call_args[0][0]
        topic = call_args[1]["topic"]

        # Verify event type and structure
        assert isinstance(published_event, TenantResumedEvent)
        assert published_event.event_type == "tenant.tenant.resumed"
        assert topic == "tenant.lifecycle"

        # Verify event data
        assert published_event.data.tenant_id == "tenant-123"
        assert published_event.data.tenant_slug == "test-tenant"
        assert published_event.data.tenant_name == "Test Tenant"
        assert published_event.data.suspension_reason == "Payment overdue"
        assert published_event.data.suspended_at == datetime.fromisoformat(
            "2026-01-05T10:00:00+00:00"
        )
        assert isinstance(published_event.data.resumed_at, datetime)

        # Verify envelope fields
        assert published_event.source_service == "registry-service"
        assert published_event.metadata["subject_tenant_id"] == "tenant-123"

    @pytest.mark.asyncio
    async def test_resume_tenant_handles_missing_suspension_info(self):
        """Test that resume event handles missing suspension info gracefully."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))

        # Mock tenant with missing suspension info
        tenant_data = {
            "id": "tenant-123",
            "slug": "test-tenant",
            "name": "Test Tenant",
            "status": "suspended",
            "config": {"quotas": {"max_users": 50}},  # No suspension_reason or suspended_at
            "keycloak_org_id": "org-123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
        }
        conn.fetchrow.return_value = tenant_data

        service = TenantService()
        service._pool = pool
        service._event_publisher.publish = AsyncMock()

        # Execute resumption
        await service.resume_tenant("tenant-123")

        # Verify event was still published with defaults
        service._event_publisher.publish.assert_called_once()

        call_args = service._event_publisher.publish.call_args
        published_event = call_args[0][0]

        # Should have default values for missing info
        assert published_event.data.suspension_reason == "Unknown"
        assert isinstance(published_event.data.suspended_at, datetime)


class TestTenantServiceDeleteEventEmission:
    """Tests for tenant deletion event emission."""

    @pytest.fixture
    def mock_pool_with_tenant(self):
        """Mock database pool with existing tenant."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))

        # Mock active tenant data
        tenant_data = {
            "id": "tenant-123",
            "slug": "test-tenant",
            "name": "Test Tenant",
            "status": "active",
            "config": {"quotas": {"max_users": 50}},
            "keycloak_org_id": "org-123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
        }
        conn.fetchrow.return_value = tenant_data

        return pool, conn

    @pytest.mark.asyncio
    async def test_delete_tenant_emits_structured_event(self, mock_pool_with_tenant):
        """Test that delete_tenant emits properly structured TenantDeletedEvent."""
        pool, conn = mock_pool_with_tenant

        service = TenantService()
        service._pool = pool
        service._event_publisher.publish = AsyncMock()

        # Execute deletion
        reason = "Customer requested account closure"
        await service.delete_tenant("tenant-123", reason)

        # Verify structured event was published
        service._event_publisher.publish.assert_called_once()

        # Get the event from the call
        call_args = service._event_publisher.publish.call_args
        published_event = call_args[0][0]
        topic = call_args[1]["topic"]

        # Verify event type and structure
        assert isinstance(published_event, TenantDeletedEvent)
        assert published_event.event_type == "tenant.tenant.deleted"
        assert topic == "tenant.lifecycle"

        # Verify event data
        assert published_event.data.tenant_id == "tenant-123"
        assert published_event.data.tenant_slug == "test-tenant"
        assert published_event.data.tenant_name == "Test Tenant"
        assert published_event.data.reason == reason
        assert published_event.data.previous_status == TenantEventStatus.ACTIVE
        assert isinstance(published_event.data.deleted_at, datetime)
        assert isinstance(published_event.data.purge_at, datetime)

        # Verify envelope fields
        assert published_event.source_service == "registry-service"
        assert published_event.metadata["subject_tenant_id"] == "tenant-123"
        assert published_event.metadata["deletion_reason"] == reason


class TestTenantServiceUpdateEventEmission:
    """Tests for tenant update event emission."""

    @pytest.fixture
    def mock_pool_with_tenant(self):
        """Mock database pool with existing tenant."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))

        # Mock active tenant data
        tenant_data = {
            "id": "tenant-123",
            "slug": "test-tenant",
            "name": "Test Tenant",
            "status": "active",
            "config": {"quotas": {"max_users": 50}},
            "keycloak_org_id": "org-123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
        }

        # Return tenant data twice (for get and after update)
        conn.fetchrow.side_effect = [tenant_data, {**tenant_data, "name": "Updated Test Tenant"}]

        return pool, conn

    @pytest.mark.asyncio
    async def test_update_tenant_emits_structured_event(self, mock_pool_with_tenant):
        """Test that update_tenant emits properly structured TenantUpdatedEvent."""
        pool, conn = mock_pool_with_tenant

        service = TenantService()
        service._pool = pool
        service._event_publisher.publish = AsyncMock()

        # Execute update
        await service.update_tenant(
        updated_tenant = await service.update_tenant(
            "tenant-123", name="Updated Test Tenant", config={"quotas": {"max_users": 100}}
        )

        # Verify structured event was published
        service._event_publisher.publish.assert_called_once()

        # Get the event from the call
        call_args = service._event_publisher.publish.call_args
        published_event = call_args[0][0]
        topic = call_args[1]["topic"]

        # Verify event type and structure
        assert isinstance(published_event, TenantUpdatedEvent)
        assert published_event.event_type == "tenant.tenant.updated"
        assert topic == "tenant.lifecycle"

        # Verify event data
        assert published_event.data.tenant_id == "tenant-123"
        assert published_event.data.tenant_slug == "test-tenant"
        assert published_event.data.tenant_name == "Updated Test Tenant"
        assert set(published_event.data.changed_fields) == {"name", "config", "updated_at"}
        assert "name" in published_event.data.previous_values
        assert "config" in published_event.data.previous_values
        assert "updated_at" in published_event.data.previous_values
        assert isinstance(published_event.data.updated_at, datetime)

        # Verify envelope fields
        assert published_event.source_service == "registry-service"
        assert published_event.metadata["subject_tenant_id"] == "tenant-123"
        assert published_event.metadata["changed_field_count"] == "3"

    @pytest.mark.asyncio
    async def test_update_tenant_no_event_when_no_changes(self, mock_pool_with_tenant):
        """Test that update_tenant doesn't emit event when no changes made."""
        pool, conn = mock_pool_with_tenant

        service = TenantService()
        service._pool = pool
        service._event_publisher.publish = AsyncMock()

        # Execute update with no actual changes
        await service.update_tenant("tenant-123")  # No name or config changes

        # Verify no event was published since no changes were made
        service._event_publisher.publish.assert_not_called()


class TestTenantServiceEventEmissionIntegration:
    """Integration tests for event emission across tenant lifecycle."""

    @pytest.mark.asyncio
    async def test_complete_tenant_lifecycle_events(self):
        """Test that all events are emitted correctly through complete tenant lifecycle."""
        service = TenantService()

        # Mock database connection
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire = MagicMock(return_value=MockAsyncContextManager(conn))
        service._pool = pool

        # Mock event publisher to track all events
        events_published = []

        async def mock_publish(event, topic=None):
            events_published.append((event, topic))

        service._event_publisher.publish = AsyncMock(side_effect=mock_publish)

        # Mock Keycloak operations
        with patch.object(service, "_create_keycloak_organization") as mock_keycloak, patch.object(
            service, "_invite_admin_user"
        ):
        ) as mock_invite:
            mock_keycloak.return_value = "org-lifecycle-test"

            # Phase 1: Create tenant
            conn.fetchrow.return_value = None  # No existing tenant
            conn.execute.return_value = None

            created_tenant = await service.create_tenant(
                slug="lifecycle-test",
                name="Lifecycle Test Tenant",
                admin_email="admin@lifecycle.com",
            )

            # Verify creation event
            assert len(events_published) == 1
            create_event, topic = events_published[0]
            assert isinstance(create_event, TenantCreatedEvent)
            assert topic == "tenant.lifecycle"

            # Phase 2: Suspend tenant
            events_published.clear()
            conn.fetchrow.return_value = {
                "id": created_tenant.id,
                "slug": "lifecycle-test",
                "name": "Lifecycle Test Tenant",
                "status": "active",
                "config": {},
                "keycloak_org_id": "org-lifecycle-test",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "deleted_at": None,
            }

            await service.suspend_tenant(created_tenant.id, "Testing suspension")

            # Verify suspension event
            assert len(events_published) == 1
            suspend_event, topic = events_published[0]
            assert isinstance(suspend_event, TenantSuspendedEvent)

            # Phase 3: Resume tenant
            events_published.clear()
            conn.fetchrow.return_value = {
                "id": created_tenant.id,
                "slug": "lifecycle-test",
                "name": "Lifecycle Test Tenant",
                "status": "suspended",
                "config": {
                    "suspension_reason": "Testing suspension",
                    "suspended_at": "2026-01-05T10:00:00+00:00",
                },
                "keycloak_org_id": "org-lifecycle-test",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "deleted_at": None,
            }

            await service.resume_tenant(created_tenant.id)

            # Verify resume event
            assert len(events_published) == 1
            resume_event, topic = events_published[0]
            assert isinstance(resume_event, TenantResumedEvent)

            # Phase 4: Update tenant
            events_published.clear()
            conn.fetchrow.side_effect = [
                {  # First call for get_tenant_by_id
                    "id": created_tenant.id,
                    "slug": "lifecycle-test",
                    "name": "Lifecycle Test Tenant",
                    "status": "active",
                    "config": {},
                    "keycloak_org_id": "org-lifecycle-test",
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "deleted_at": None,
                },
                {  # Second call after update
                    "id": created_tenant.id,
                    "slug": "lifecycle-test",
                    "name": "Updated Lifecycle Test Tenant",
                    "status": "active",
                    "config": {},
                    "keycloak_org_id": "org-lifecycle-test",
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "deleted_at": None,
                },
            ]

            await service.update_tenant(created_tenant.id, name="Updated Lifecycle Test Tenant")
            updated_tenant = await service.update_tenant(
                created_tenant.id, name="Updated Lifecycle Test Tenant"
            )

            # Verify update event
            assert len(events_published) == 1
            update_event, topic = events_published[0]
            assert isinstance(update_event, TenantUpdatedEvent)

            # Phase 5: Delete tenant
            events_published.clear()
            conn.fetchrow.return_value = {
                "id": created_tenant.id,
                "slug": "lifecycle-test",
                "name": "Updated Lifecycle Test Tenant",
                "status": "active",
                "config": {},
                "keycloak_org_id": "org-lifecycle-test",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "deleted_at": None,
            }

            await service.delete_tenant(created_tenant.id, "Test complete")

            # Verify deletion event
            assert len(events_published) == 1
            delete_event, topic = events_published[0]
            assert isinstance(delete_event, TenantDeletedEvent)
            assert topic == "tenant.lifecycle"
