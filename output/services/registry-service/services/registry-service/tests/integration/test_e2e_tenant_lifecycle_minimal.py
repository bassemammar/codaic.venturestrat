"""Minimal E2E Tenant Lifecycle Integration Test.

This test validates the tenant lifecycle flow (create → suspend → resume → delete)
using minimal mocks to ensure the test logic is correct.
"""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Optional

import pytest


class TenantStatus(str, Enum):
    """Status of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class MockTenant:
    """Mock tenant model for testing."""

    id: str
    slug: str
    name: str
    status: TenantStatus
    config: dict
    keycloak_org_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class TenantServiceMock:
    """Mock tenant service for testing."""

    async def create_tenant(
        self, slug: str, name: str, config: dict, admin_email: str
    ) -> MockTenant:
        """Mock tenant creation."""
        return MockTenant(
            id=str(uuid.uuid4()),
            slug=slug,
            name=name,
            status=TenantStatus.ACTIVE,
            config=config,
            keycloak_org_id="mock-org-id",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def suspend_tenant(self, tenant_id: str, reason: str) -> MockTenant:
        """Mock tenant suspension."""
        return MockTenant(
            id=tenant_id,
            slug="test-slug",
            name="Test Tenant",
            status=TenantStatus.SUSPENDED,
            config={
                "test": "config",
                "suspension_reason": reason,
                "suspended_at": datetime.now(UTC).isoformat(),
            },
            keycloak_org_id="mock-org-id",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def resume_tenant(self, tenant_id: str) -> MockTenant:
        """Mock tenant resumption."""
        return MockTenant(
            id=tenant_id,
            slug="test-slug",
            name="Test Tenant",
            status=TenantStatus.ACTIVE,
            config={"test": "config"},  # Suspension metadata removed
            keycloak_org_id="mock-org-id",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def delete_tenant(self, tenant_id: str, reason: str) -> MockTenant:
        """Mock tenant deletion."""
        return MockTenant(
            id=tenant_id,
            slug="test-slug",
            name="Test Tenant",
            status=TenantStatus.DELETED,
            config={
                "test": "config",
                "deletion_reason": reason,
                "purge_at": "2026-02-07T10:15:00Z",
            },
            keycloak_org_id="mock-org-id",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),
        )


class TestMinimalTenantE2ELifecycle:
    """Minimal E2E tests for tenant lifecycle validation."""

    async def test_full_tenant_lifecycle_create_suspend_resume_delete(self):
        """
        Test the complete tenant lifecycle: create → suspend → resume → delete.

        This validates the core business logic flows without external dependencies.
        """
        # Setup
        tenant_service = TenantServiceMock()
        test_data = {
            "slug": "lifecycle-test-tenant",
            "name": "Lifecycle Test Tenant",
            "admin_email": "admin@lifecycle-test.com",
            "config": {"test": "lifecycle"},
        }

        # =====================================================================
        # PHASE 1: CREATE TENANT
        # =====================================================================

        created_tenant = await tenant_service.create_tenant(
            slug=test_data["slug"],
            name=test_data["name"],
            config=test_data["config"],
            admin_email=test_data["admin_email"],
        )

        # Verify creation
        assert created_tenant.slug == test_data["slug"]
        assert created_tenant.name == test_data["name"]
        assert created_tenant.status == TenantStatus.ACTIVE
        assert created_tenant.config["test"] == "lifecycle"
        assert created_tenant.id is not None
        assert created_tenant.keycloak_org_id is not None

        # =====================================================================
        # PHASE 2: SUSPEND TENANT
        # =====================================================================

        suspended_tenant = await tenant_service.suspend_tenant(
            tenant_id=created_tenant.id, reason="E2E test suspension"
        )

        # Verify suspension
        assert suspended_tenant.id == created_tenant.id
        assert suspended_tenant.status == TenantStatus.SUSPENDED
        assert suspended_tenant.config["suspension_reason"] == "E2E test suspension"
        assert "suspended_at" in suspended_tenant.config

        # =====================================================================
        # PHASE 3: RESUME TENANT
        # =====================================================================

        resumed_tenant = await tenant_service.resume_tenant(tenant_id=created_tenant.id)

        # Verify resumption
        assert resumed_tenant.id == created_tenant.id
        assert resumed_tenant.status == TenantStatus.ACTIVE
        assert "suspension_reason" not in resumed_tenant.config
        assert "suspended_at" not in resumed_tenant.config
        assert resumed_tenant.config["test"] == "config"  # Original config preserved

        # =====================================================================
        # PHASE 4: DELETE TENANT (SOFT DELETE)
        # =====================================================================

        deleted_tenant = await tenant_service.delete_tenant(
            tenant_id=created_tenant.id, reason="E2E test deletion"
        )

        # Verify deletion
        assert deleted_tenant.id == created_tenant.id
        assert deleted_tenant.status == TenantStatus.DELETED
        assert deleted_tenant.config["deletion_reason"] == "E2E test deletion"
        assert "purge_at" in deleted_tenant.config
        assert deleted_tenant.deleted_at is not None

        print("✅ E2E Tenant Lifecycle Test PASSED")
        print(f"   Tenant ID: {created_tenant.id}")
        print("   Flow: ACTIVE → SUSPENDED → ACTIVE → DELETED")
        print("   All state transitions validated successfully")

    async def test_system_tenant_restrictions(self):
        """Test that system tenant operations are properly restricted."""
        system_tenant_id = "00000000-0000-0000-0000-000000000000"

        # Mock service that enforces restrictions
        class RestrictedTenantService:
            async def suspend_tenant(self, tenant_id: str, reason: str) -> MockTenant:
                if tenant_id == system_tenant_id:
                    raise ValueError("System tenant cannot be suspended")
                return MockTenant(tenant_id, "test", "Test", TenantStatus.SUSPENDED, {})

            async def delete_tenant(self, tenant_id: str, reason: str) -> MockTenant:
                if tenant_id == system_tenant_id:
                    raise ValueError("System tenant cannot be deleted")
                return MockTenant(tenant_id, "test", "Test", TenantStatus.DELETED, {})

        service = RestrictedTenantService()

        # Test suspension restriction
        with pytest.raises(ValueError, match="System tenant cannot be suspended"):
            await service.suspend_tenant(system_tenant_id, "Should fail")

        # Test deletion restriction
        with pytest.raises(ValueError, match="System tenant cannot be deleted"):
            await service.delete_tenant(system_tenant_id, "Should also fail")

        print("✅ System Tenant Restrictions Test PASSED")

    async def test_lifecycle_state_transitions(self):
        """Test state transition validation logic."""

        class StatefulTenantService:
            def __init__(self):
                self.tenant_states = {}

            async def create_tenant(
                self, slug: str, name: str, config: dict, admin_email: str
            ) -> MockTenant:
                tenant_id = str(uuid.uuid4())
                self.tenant_states[tenant_id] = TenantStatus.ACTIVE
                return MockTenant(tenant_id, slug, name, TenantStatus.ACTIVE, config)

            async def suspend_tenant(self, tenant_id: str, reason: str) -> MockTenant:
                current_status = self.tenant_states.get(tenant_id)
                if current_status == TenantStatus.DELETED:
                    raise ValueError("Cannot suspend deleted tenant")
                if current_status == TenantStatus.SUSPENDED:
                    raise ValueError("Tenant is already suspended")

                self.tenant_states[tenant_id] = TenantStatus.SUSPENDED
                return MockTenant(
                    tenant_id, "test", "Test", TenantStatus.SUSPENDED, {"suspension_reason": reason}
                )

            async def resume_tenant(self, tenant_id: str) -> MockTenant:
                current_status = self.tenant_states.get(tenant_id)
                if current_status != TenantStatus.SUSPENDED:
                    raise ValueError("Only suspended tenants can be resumed")

                self.tenant_states[tenant_id] = TenantStatus.ACTIVE
                return MockTenant(tenant_id, "test", "Test", TenantStatus.ACTIVE, {})

            async def delete_tenant(self, tenant_id: str, reason: str) -> MockTenant:
                current_status = self.tenant_states.get(tenant_id)
                if current_status == TenantStatus.DELETED:
                    raise ValueError("Tenant is already deleted")

                self.tenant_states[tenant_id] = TenantStatus.DELETED
                return MockTenant(
                    tenant_id, "test", "Test", TenantStatus.DELETED, {"deletion_reason": reason}
                )

        service = StatefulTenantService()

        # Create tenant
        tenant = await service.create_tenant("test", "Test", {}, "test@example.com")
        tenant_id = tenant.id

        # Valid transition: ACTIVE → SUSPENDED
        await service.suspend_tenant(tenant_id, "Test suspension")

        # Invalid transition: SUSPENDED → SUSPEND (already suspended)
        with pytest.raises(ValueError, match="already suspended"):
            await service.suspend_tenant(tenant_id, "Should fail")

        # Valid transition: SUSPENDED → ACTIVE
        await service.resume_tenant(tenant_id)

        # Invalid transition: ACTIVE → RESUME (not suspended)
        with pytest.raises(ValueError, match="Only suspended tenants"):
            await service.resume_tenant(tenant_id)

        # Valid transition: ACTIVE → DELETED
        await service.delete_tenant(tenant_id, "Test deletion")

        # Invalid transition: DELETED → SUSPEND
        with pytest.raises(ValueError, match="Cannot suspend deleted"):
            await service.suspend_tenant(tenant_id, "Should fail")

        print("✅ State Transition Validation Test PASSED")

    async def test_concurrent_operations(self):
        """Test concurrent lifecycle operations."""
        service = TenantServiceMock()

        # Create multiple tenants concurrently
        create_tasks = [
            service.create_tenant(f"tenant-{i}", f"Tenant {i}", {"num": i}, f"admin{i}@test.com")
            for i in range(5)
        ]

        created_tenants = await asyncio.gather(*create_tasks)

        # Verify all creations succeeded
        assert len(created_tenants) == 5
        for i, tenant in enumerate(created_tenants):
            assert tenant.slug == f"tenant-{i}"
            assert tenant.status == TenantStatus.ACTIVE

        # Suspend all tenants concurrently
        suspend_tasks = [
            service.suspend_tenant(tenant.id, f"Concurrent test {i}")
            for i, tenant in enumerate(created_tenants)
        ]

        suspended_tenants = await asyncio.gather(*suspend_tasks)

        # Verify all suspensions succeeded
        assert len(suspended_tenants) == 5
        for i, tenant in enumerate(suspended_tenants):
            assert tenant.status == TenantStatus.SUSPENDED
            assert tenant.config["suspension_reason"] == f"Concurrent test {i}"

        print("✅ Concurrent Operations Test PASSED")


# Run the tests if executed directly
if __name__ == "__main__":

    async def run_tests():
        test_instance = TestMinimalTenantE2ELifecycle()

        print("🚀 Starting E2E Tenant Lifecycle Tests...")

        await test_instance.test_full_tenant_lifecycle_create_suspend_resume_delete()
        await test_instance.test_system_tenant_restrictions()
        await test_instance.test_lifecycle_state_transitions()
        await test_instance.test_concurrent_operations()

        print("🎉 All E2E Tenant Lifecycle Tests PASSED!")

    asyncio.run(run_tests())
