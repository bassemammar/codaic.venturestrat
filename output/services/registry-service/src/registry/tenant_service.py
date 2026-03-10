"""Tenant management service for Registry Service.

This module provides the TenantService class for managing tenants,
including system tenant initialization and database operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None

import structlog
from pydantic import ValidationError
from venturestrat.tenancy.events import TenantStatus as TenantEventStatus
from venturestrat.tenancy.events import (
    create_tenant_created_event,
    create_tenant_deleted_event,
    create_tenant_resumed_event,
    create_tenant_suspended_event,
    create_tenant_updated_event,
)
from venturestrat_service_base.events import EventPublisher

from registry.config import settings
from registry.keycloak_client import KeycloakClient, KeycloakClientError
from registry.models import Tenant, TenantStatus

logger = structlog.get_logger(__name__)


class TenantService:
    """Service for managing tenants in the Registry Service.

    Handles tenant lifecycle operations including:
    - System tenant initialization
    - Database connections and queries
    - Tenant CRUD operations
    """

    SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000000"
    SYSTEM_TENANT_SLUG = "system"

    def __init__(self, database_url: str | None = None):
        """Initialize the tenant service.

        Args:
            database_url: PostgreSQL connection URL. Uses settings.database_url if not provided.
        """
        self.database_url = database_url or settings.database_url
        self._pool = None

        # Initialize event publisher and Keycloak client
        self._event_publisher = EventPublisher(settings)
        self._keycloak_client = KeycloakClient()

    async def initialize(self) -> None:
        """Initialize the tenant service and database connection."""
        if asyncpg is None:
            raise RuntimeError(
                "asyncpg is required for database operations. Install with: pip install asyncpg"
            )

        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=30,
                ssl=False,  # Disable SSL for local development
                server_settings={"search_path": "registry,public"},
            )

            # Initialize event publisher and Keycloak client
            try:
                await self._event_publisher.start()
                await self._keycloak_client.start()
                logger.info("tenant_service_external_services_started")
            except Exception as e:
                logger.warning("tenant_service_external_services_failed", error=str(e))
                # Continue without external services - they're not critical for basic operations

            # Ensure system tenant exists
            await self.ensure_system_tenant()

            logger.info(
                "tenant_service_initialized",
                database_url=self.database_url,
                system_tenant_id=self.SYSTEM_TENANT_ID,
            )

        except Exception as e:
            logger.error("failed_to_initialize_tenant_service", error=str(e))
            raise

    async def close(self) -> None:
        """Close database connections and external services."""
        try:
            await self._event_publisher.stop()
            await self._keycloak_client.close()
            logger.info("tenant_service_external_services_stopped")
        except Exception as e:
            logger.warning("tenant_service_external_services_stop_failed", error=str(e))

        if self._pool:
            await self._pool.close()
            logger.info("tenant_service_closed")

    async def ensure_system_tenant(self) -> Tenant:
        """Ensure the system tenant exists in the database.

        Creates the system tenant if it doesn't exist, otherwise returns existing one.
        This is idempotent - safe to call multiple times.

        Returns:
            System tenant instance

        Raises:
            RuntimeError: If database connection not initialized
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            # Try to find existing system tenant
            row = await conn.fetchrow(
                "SELECT id, slug, name, status, config, keycloak_org_id, "
                "created_at, updated_at, deleted_at FROM tenants WHERE id = $1",
                self.SYSTEM_TENANT_ID,
            )

            if row:
                # System tenant already exists
                tenant = Tenant(
                    id=row["id"],
                    slug=row["slug"],
                    name=row["name"],
                    status=row["status"],
                    config=row["config"] or {},
                    keycloak_org_id=row["keycloak_org_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    deleted_at=row["deleted_at"],
                )

                logger.info(
                    "system_tenant_found",
                    tenant_id=tenant.id,
                    slug=tenant.slug,
                    status=tenant.status,
                )
                return tenant

            # Create system tenant
            system_tenant = Tenant.create_system_tenant()

            # Insert into database
            # Convert config dict to JSON string for asyncpg
            import json

            config_json = json.dumps(system_tenant.config)

            await conn.execute(
                """
                INSERT INTO tenants (id, slug, name, status, config, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW())
                """,
                system_tenant.id,
                system_tenant.slug,
                system_tenant.name,
                system_tenant.status,
                config_json,
            )

            logger.info(
                "system_tenant_created",
                tenant_id=system_tenant.id,
                slug=system_tenant.slug,
                status=system_tenant.status,
            )

            return system_tenant

    async def get_tenant_by_id(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Tenant instance or None if not found
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, slug, name, status, config, keycloak_org_id, "
                "created_at, updated_at, deleted_at FROM tenants WHERE id = $1 AND deleted_at IS NULL",
                tenant_id,
            )

            if not row:
                return None

            return Tenant(
                id=row["id"],
                slug=row["slug"],
                name=row["name"],
                status=row["status"],
                config=row["config"] or {},
                keycloak_org_id=row["keycloak_org_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                deleted_at=row["deleted_at"],
            )

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        """Get a tenant by slug.

        Args:
            slug: URL-friendly tenant identifier

        Returns:
            Tenant instance or None if not found
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, slug, name, status, config, keycloak_org_id, "
                "created_at, updated_at, deleted_at FROM tenants WHERE slug = $1 AND deleted_at IS NULL",
                slug,
            )

            if not row:
                return None

            return Tenant(
                id=row["id"],
                slug=row["slug"],
                name=row["name"],
                status=row["status"],
                config=row["config"] or {},
                keycloak_org_id=row["keycloak_org_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                deleted_at=row["deleted_at"],
            )

    async def get_system_tenant(self) -> Tenant:
        """Get the system tenant.

        Returns:
            System tenant instance

        Raises:
            RuntimeError: If system tenant not found
        """
        tenant = await self.get_tenant_by_id(self.SYSTEM_TENANT_ID)
        if not tenant:
            raise RuntimeError("System tenant not found. Database may not be initialized.")
        return tenant

    async def list_tenants(
        self,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Tenant], int]:
        """List tenants with optional filtering and pagination.

        Args:
            status: Filter by status (active, suspended, deleted)
            search: Search by name or slug
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (tenant list, total count)
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Build WHERE clause
        where_conditions = ["1=1"]
        params = []
        param_count = 0

        # Status filter
        if status:
            param_count += 1
            where_conditions.append(f"status = ${param_count}")
            params.append(status)

        # Search filter
        if search:
            param_count += 1
            param_count_2 = param_count + 1
            where_conditions.append(f"(name ILIKE ${param_count} OR slug ILIKE ${param_count_2})")
            search_term = f"%{search}%"
            params.extend([search_term, search_term])
            param_count += 1

        # Include soft-deleted tenants only if specifically requested
        if status != "deleted":
            where_conditions.append("deleted_at IS NULL")

        where_clause = " AND ".join(where_conditions)

        async with self._pool.acquire() as conn:
            # Get total count
            count_query = f"SELECT COUNT(*) FROM tenants WHERE {where_clause}"
            total = await conn.fetchval(count_query, *params)

            # Get paginated results
            offset = (page - 1) * page_size
            limit_offset_params = params + [page_size, offset]
            param_limit = param_count + 1
            param_offset = param_count + 2

            query = f"""
                SELECT id, slug, name, status, config, keycloak_org_id,
                       created_at, updated_at, deleted_at
                FROM tenants
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_limit} OFFSET ${param_offset}
            """

            rows = await conn.fetch(query, *limit_offset_params)

            tenants = [
                Tenant(
                    id=row["id"],
                    slug=row["slug"],
                    name=row["name"],
                    status=row["status"],
                    config=row["config"] or {},
                    keycloak_org_id=row["keycloak_org_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    deleted_at=row["deleted_at"],
                )
                for row in rows
            ]

            return tenants, total

    async def update_tenant(
        self, tenant_id: str, name: str | None = None, config: dict[str, Any] | None = None
    ) -> Optional[Tenant]:
        """Update a tenant's name or configuration.

        Args:
            tenant_id: UUID of the tenant to update
            name: New tenant name (optional)
            config: New configuration to merge (optional)

        Returns:
            Updated tenant instance or None if not found
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Get the current tenant
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        # Cannot update system tenant
        if tenant.id == self.SYSTEM_TENANT_ID:
            raise ValueError("Cannot update system tenant")

        # Prepare updates
        updates = {}
        if name is not None:
            updates["name"] = name

        if config is not None:
            # Merge with existing config
            merged_config = tenant.config.copy()
            merged_config.update(config)
            updates["config"] = merged_config

        if not updates:
            # Nothing to update
            return tenant

        # Always update the timestamp
        updates["updated_at"] = datetime.now(UTC)

        # Build update query
        set_clauses = []
        params = []
        param_count = 0

        for field, value in updates.items():
            param_count += 1
            set_clauses.append(f"{field} = ${param_count}")
            params.append(value)

        # Add tenant_id parameter
        param_count += 1
        params.append(tenant_id)

        set_clause = ", ".join(set_clauses)
        query = f"""
            UPDATE tenants
            SET {set_clause}
            WHERE id = ${param_count}
        """

        async with self._pool.acquire() as conn:
            await conn.execute(query, *params)

        logger.info("tenant_updated", tenant_id=tenant_id, updates=list(updates.keys()))

        # Get the updated tenant
        updated_tenant = await self.get_tenant_by_id(tenant_id)

        # Emit tenant updated event
        if updated_tenant:
            await self._emit_tenant_updated_event(
                tenant=updated_tenant,
                changed_fields=list(updates.keys()),
                previous_values={field: getattr(tenant, field, None) for field in updates.keys()},
                current_values={
                    field: getattr(updated_tenant, field, None) for field in updates.keys()
                },
            )

        return updated_tenant

    async def create_tenant(
        self,
        slug: str,
        name: str,
        config: dict[str, Any] | None = None,
        admin_email: str | None = None,
    ) -> Tenant:
        """Create a new tenant.

        This method performs the complete tenant creation flow:
        1. Validates slug uniqueness
        2. Creates Keycloak organization (if configured)
        3. Creates tenant record in database
        4. Invites admin user (if email provided)
        5. Emits tenant creation event

        Args:
            slug: URL-friendly tenant identifier
            name: Human-readable tenant name
            config: Optional tenant configuration (quotas, theme, etc.)
            admin_email: Optional admin user email for invitation

        Returns:
            Created Tenant instance

        Raises:
            ValueError: If slug is already taken or validation fails
            RuntimeError: If database operation fails
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Validate slug uniqueness
        existing_tenant = await self.get_tenant_by_slug(slug)
        if existing_tenant:
            raise ValueError(f"Tenant with slug '{slug}' already exists")

        # Create tenant instance with provided or default config
        tenant_config = config or {}

        # Step 1: Validate tenant data by creating instance (this will validate slug format)
        try:
            # Create tenant instance with placeholder keycloak_org_id for validation
            Tenant(
                slug=slug,
                name=name,
                config=tenant_config,
                keycloak_org_id=None,  # Will be set later after Keycloak org creation
            )
        except ValidationError as e:
            logger.error("tenant_validation_failed", slug=slug, name=name, error=str(e))
            raise ValueError(f"Tenant validation failed: {e}") from e

        # Step 2: Create Keycloak organization (placeholder for now)
        keycloak_org_id = await self._create_keycloak_organization(slug, name)

        # Step 3: Create final tenant instance with keycloak_org_id
        tenant = Tenant(slug=slug, name=name, config=tenant_config, keycloak_org_id=keycloak_org_id)

        # Step 4: Insert tenant record into database
        async with self._pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO tenants (id, slug, name, status, config, keycloak_org_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    """,
                    tenant.id,
                    tenant.slug,
                    tenant.name,
                    tenant.status,
                    tenant.config,
                    tenant.keycloak_org_id,
                )

                logger.info(
                    "tenant_created",
                    tenant_id=tenant.id,
                    slug=tenant.slug,
                    name=tenant.name,
                    keycloak_org_id=keycloak_org_id,
                )

            except Exception as e:
                logger.error("failed_to_create_tenant", slug=slug, name=name, error=str(e))
                raise RuntimeError(f"Failed to create tenant: {e}") from e

        # Step 5: Invite admin user (if email provided)
        if admin_email:
            await self._invite_admin_user(tenant, admin_email)

        # Step 6: Emit tenant creation event
        await self._emit_tenant_created_event(tenant, admin_email)

        return tenant

    async def _create_keycloak_organization(self, slug: str, name: str) -> str | None:
        """Create Keycloak organization for tenant.

        This method creates a Keycloak organization with:
        1. Organization record with slug and name
        2. Basic configuration and attributes
        3. Returns organization ID for tenant record

        Args:
            slug: Tenant slug (used as organization identifier)
            name: Tenant display name

        Returns:
            Keycloak organization ID or None if Keycloak unavailable
        """
        try:
            # Use the actual Keycloak client to create organization
            org_id = await self._keycloak_client.create_organization(slug, name)

            logger.info("keycloak_organization_created", slug=slug, name=name, org_id=org_id)

            return org_id

        except KeycloakClientError as e:
            # Log warning but don't fail tenant creation - Keycloak is optional
            logger.warning(
                "keycloak_organization_creation_failed",
                slug=slug,
                name=name,
                error=str(e),
                message="Tenant will be created without Keycloak organization",
            )

            # Return None - tenant can still function without Keycloak
            return None

    async def _invite_admin_user(self, tenant: Tenant, admin_email: str) -> None:
        """Invite admin user to tenant.

        This method invites an admin user to the tenant by:
        1. Creating user in Keycloak organization (if available)
        2. Assigning admin roles
        3. Sending invitation email via Keycloak
        4. Setting up initial user profile with tenant_admin attributes

        Args:
            tenant: Created tenant instance
            admin_email: Admin user email address
        """
        # Only invite if we have a Keycloak organization
        if not tenant.keycloak_org_id:
            logger.info(
                "admin_user_invitation_skipped_no_keycloak",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                admin_email=admin_email,
                message="No Keycloak organization available for user invitation",
            )
            return

        try:
            # Invite user to Keycloak organization with admin role
            user_id = await self._keycloak_client.invite_user_to_organization(
                org_id=tenant.keycloak_org_id,
                email=admin_email,
                first_name=None,  # Let user set these during signup
                last_name=None,
                roles=["admin"],
            )

            logger.info(
                "admin_user_invited",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                admin_email=admin_email,
                keycloak_user_id=user_id,
                keycloak_org_id=tenant.keycloak_org_id,
            )

        except KeycloakClientError as e:
            # Log error but don't fail tenant creation - user can be invited later
            logger.error(
                "admin_user_invitation_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                admin_email=admin_email,
                keycloak_org_id=tenant.keycloak_org_id,
                error=str(e),
                message="Admin user invitation failed, but tenant creation continues",
            )

    async def _emit_tenant_created_event(
        self, tenant: Tenant, admin_email: str | None = None
    ) -> None:
        """Emit tenant creation event for downstream services.

        This method publishes a tenant creation event that notifies:
        1. Other services to initialize tenant-specific resources
        2. Monitoring and analytics systems
        3. Billing and quota systems
        4. Audit trail for compliance

        Args:
            tenant: Created tenant instance
            admin_email: Optional admin email for context
        """
        try:
            # Create structured event using the new tenant event schemas
            event = create_tenant_created_event(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                created_at=tenant.created_at,
                config=tenant.config,
                keycloak_org_id=tenant.keycloak_org_id,
                admin_email=admin_email,
                source_service="registry-service",
                tenant_context_id=None,  # Use None for system context
            )

            # Publish via the new event publisher
            await self._event_publisher.publish(event, topic="tenant.lifecycle")

            logger.info(
                "tenant_created_event_published",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                keycloak_org_id=tenant.keycloak_org_id,
                admin_email=admin_email,
                created_at=tenant.created_at.isoformat(),
            )

        except Exception as e:
            # Log error but don't fail tenant creation - event can be retried
            logger.error(
                "tenant_created_event_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                error=str(e),
                message="Tenant creation event failed, but tenant was created successfully",
            )

    async def _emit_tenant_suspended_event(
        self, tenant: Tenant, reason: str, previous_status: TenantStatus
    ) -> None:
        """Emit tenant suspension event for downstream services.

        Args:
            tenant: Suspended tenant instance
            reason: Reason for suspension
            previous_status: Status before suspension
        """
        try:
            # Convert enum to TenantEventStatus for event
            event_previous_status = TenantEventStatus(previous_status)

            # Create structured event
            event = create_tenant_suspended_event(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                reason=reason,
                previous_status=event_previous_status,
                suspended_at=datetime.fromisoformat(tenant.config.get("suspended_at")),
                source_service="registry-service",
                tenant_context_id=None,  # Use None for system context
            )

            # Publish the event
            await self._event_publisher.publish(event, topic="tenant.lifecycle")

            logger.info(
                "tenant_suspended_event_published",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                reason=reason,
                suspended_at=tenant.config.get("suspended_at"),
            )

        except Exception as e:
            logger.error(
                "tenant_suspended_event_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                error=str(e),
                message="Tenant suspension event failed, but tenant was suspended successfully",
            )

    async def _emit_tenant_resumed_event(self, tenant: Tenant) -> None:
        """Emit tenant resume event for downstream services.

        Args:
            tenant: Resumed tenant instance
        """
        try:
            # Extract suspension information from config
            suspended_at_str = tenant.config.get("suspended_at")
            suspension_reason = tenant.config.get("suspension_reason", "Unknown")

            if not suspended_at_str:
                logger.warning(
                    "tenant_resumed_event_missing_suspension_info",
                    tenant_id=tenant.id,
                    message="Missing suspension_at in tenant config, using current time",
                )
                suspended_at = datetime.now(UTC)
            else:
                suspended_at = datetime.fromisoformat(suspended_at_str)

            # Create structured event
            event = create_tenant_resumed_event(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                suspended_at=suspended_at,
                suspension_reason=suspension_reason,
                source_service="registry-service",
                tenant_context_id=None,  # Use None for system context
            )

            # Publish the event
            await self._event_publisher.publish(event, topic="tenant.lifecycle")

            logger.info(
                "tenant_resumed_event_published",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                suspended_at=suspended_at_str,
                suspension_reason=suspension_reason,
            )

        except Exception as e:
            logger.error(
                "tenant_resumed_event_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                error=str(e),
                message="Tenant resume event failed, but tenant was resumed successfully",
            )

    async def _emit_tenant_updated_event(
        self,
        tenant: Tenant,
        changed_fields: list[str],
        previous_values: dict[str, Any],
        current_values: dict[str, Any],
    ) -> None:
        """Emit tenant update event for downstream services.

        Args:
            tenant: Updated tenant instance
            changed_fields: List of fields that were modified
            previous_values: Previous values for changed fields
            current_values: Current values for changed fields
        """
        try:
            # Create structured event
            event = create_tenant_updated_event(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                changed_fields=changed_fields,
                previous_values=previous_values,
                current_values=current_values,
                source_service="registry-service",
                tenant_context_id=None,  # Use None for system context
            )

            # Publish the event
            await self._event_publisher.publish(event, topic="tenant.lifecycle")

            logger.info(
                "tenant_updated_event_published",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                changed_fields=changed_fields,
                field_count=len(changed_fields),
            )

        except Exception as e:
            logger.error(
                "tenant_updated_event_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                error=str(e),
                message="Tenant update event failed, but tenant was updated successfully",
            )

    async def suspend_tenant(self, tenant_id: str, reason: str) -> Tenant | None:
        """Suspend a tenant and update database.

        Args:
            tenant_id: UUID of the tenant to suspend
            reason: Reason for suspension

        Returns:
            Suspended tenant instance or None if not found

        Raises:
            ValueError: If trying to suspend system tenant
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Get the current tenant
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        # Cannot suspend system tenant
        if tenant.id == self.SYSTEM_TENANT_ID:
            raise ValueError("Cannot suspend system tenant")

        # Use tenant model's suspend method
        suspended_tenant = tenant.suspend(reason=reason)

        # Update database
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tenants
                SET status = $1, config = $2, updated_at = $3
                WHERE id = $4
                """,
                suspended_tenant.status,
                suspended_tenant.config,
                suspended_tenant.updated_at,
                tenant_id,
            )

        logger.info(
            "tenant_suspended",
            tenant_id=tenant_id,
            reason=reason,
            suspended_at=suspended_tenant.config.get("suspended_at"),
        )

        # Emit tenant suspension event
        await self._emit_tenant_suspended_event(suspended_tenant, reason, tenant.status)

        return suspended_tenant

    async def resume_tenant(self, tenant_id: str) -> Tenant | None:
        """Resume a suspended tenant.

        Args:
            tenant_id: UUID of the tenant to resume

        Returns:
            Resumed tenant instance or None if not found

        Raises:
            ValueError: If tenant is not suspended
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Get the current tenant
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        # Use tenant model's resume method
        resumed_tenant = tenant.resume()

        # Update database
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tenants
                SET status = $1, config = $2, updated_at = $3
                WHERE id = $4
                """,
                resumed_tenant.status,
                resumed_tenant.config,
                resumed_tenant.updated_at,
                tenant_id,
            )

        logger.info("tenant_resumed", tenant_id=tenant_id)

        # Emit tenant resume event
        await self._emit_tenant_resumed_event(resumed_tenant)

        return resumed_tenant

    async def delete_tenant(self, tenant_id: str, reason: str) -> Tenant | None:
        """Soft delete a tenant.

        Args:
            tenant_id: UUID of the tenant to delete
            reason: Reason for deletion

        Returns:
            Deleted tenant instance or None if not found

        Raises:
            ValueError: If trying to delete system tenant
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Get the current tenant
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        # Cannot delete system tenant
        if tenant.id == self.SYSTEM_TENANT_ID:
            raise ValueError("Cannot delete system tenant")

        # Use tenant model's delete method
        deleted_tenant = tenant.delete(reason=reason)

        # Update database
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tenants
                SET status = $1, config = $2, deleted_at = $3, updated_at = $4
                WHERE id = $5
                """,
                deleted_tenant.status,
                deleted_tenant.config,
                deleted_tenant.deleted_at,
                deleted_tenant.updated_at,
                tenant_id,
            )

        logger.info(
            "tenant_deleted",
            tenant_id=tenant_id,
            reason=reason,
            deleted_at=deleted_tenant.deleted_at.isoformat(),
            purge_at=deleted_tenant.config.get("purge_at"),
        )

        # Emit tenant deletion event
        await self._emit_tenant_deleted_event(deleted_tenant, reason, tenant.status)

        return deleted_tenant

    async def get_tenants_for_purge(self) -> list[Tenant]:
        """Get tenants that are eligible for purge.

        Returns tenants that have been soft deleted and are past their purge date.

        Returns:
            List of tenants eligible for purge
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, slug, name, status, config, keycloak_org_id,
                       created_at, updated_at, deleted_at
                FROM tenants
                WHERE status = 'deleted'
                  AND deleted_at IS NOT NULL
                  AND (config->>'purge_at')::timestamp with time zone <= NOW()
                """
            )

            return [
                Tenant(
                    id=row["id"],
                    slug=row["slug"],
                    name=row["name"],
                    status=row["status"],
                    config=row["config"] or {},
                    keycloak_org_id=row["keycloak_org_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    deleted_at=row["deleted_at"],
                )
                for row in rows
            ]

    async def purge_tenant(self, tenant_id: str) -> bool:
        """Permanently delete a tenant and all associated data.

        This is an irreversible operation that:
        1. Deletes the tenant record from database
        2. Emits purge event for downstream services to clean up
        3. Removes Keycloak organization (if configured)

        Args:
            tenant_id: UUID of the tenant to purge

        Returns:
            True if tenant was purged, False if not found

        Raises:
            ValueError: If tenant is not in deleted status or system tenant
            RuntimeError: If database operation fails
        """
        if not self._pool:
            raise RuntimeError("TenantService not initialized. Call initialize() first.")

        # Cannot purge system tenant
        if tenant_id == self.SYSTEM_TENANT_ID:
            raise ValueError("Cannot purge system tenant")

        # Get tenant including soft-deleted ones
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, slug, name, status, config, keycloak_org_id, "
                "created_at, updated_at, deleted_at FROM tenants WHERE id = $1",
                tenant_id,
            )

            if not row:
                return False

            tenant = Tenant(
                id=row["id"],
                slug=row["slug"],
                name=row["name"],
                status=row["status"],
                config=row["config"] or {},
                keycloak_org_id=row["keycloak_org_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                deleted_at=row["deleted_at"],
            )

            # Verify tenant is in deleted status
            if tenant.status != TenantStatus.DELETED:
                raise ValueError(f"Cannot purge tenant '{tenant.slug}' - not in deleted status")

            if tenant.deleted_at is None:
                raise ValueError(f"Cannot purge tenant '{tenant.slug}' - no deletion timestamp")

            # Delete Keycloak organization if it exists
            if tenant.keycloak_org_id:
                try:
                    deleted = await self._keycloak_client.delete_organization(
                        tenant.keycloak_org_id
                    )
                    if deleted:
                        logger.info(
                            "keycloak_organization_purged",
                            tenant_id=tenant_id,
                            tenant_slug=tenant.slug,
                            keycloak_org_id=tenant.keycloak_org_id,
                        )
                    else:
                        logger.warning(
                            "keycloak_organization_not_found",
                            tenant_id=tenant_id,
                            tenant_slug=tenant.slug,
                            keycloak_org_id=tenant.keycloak_org_id,
                        )
                except KeycloakClientError as e:
                    logger.error(
                        "keycloak_organization_purge_failed",
                        tenant_id=tenant_id,
                        tenant_slug=tenant.slug,
                        keycloak_org_id=tenant.keycloak_org_id,
                        error=str(e),
                    )
                    # Continue with tenant purge even if Keycloak cleanup fails

            # Emit purge event before deletion (for downstream services to clean up data)
            await self._emit_tenant_purge_event(tenant)

            # Delete tenant record permanently from database
            await conn.execute("DELETE FROM tenants WHERE id = $1", tenant_id)

            logger.info(
                "tenant_purged",
                tenant_id=tenant_id,
                tenant_slug=tenant.slug,
                deleted_at=tenant.deleted_at.isoformat(),
                purged_at=datetime.now(UTC).isoformat(),
            )

            return True

    async def _emit_tenant_deleted_event(
        self, tenant: Tenant, reason: str, previous_status: TenantStatus
    ) -> None:
        """Emit tenant deletion event for downstream services.

        Args:
            tenant: Deleted tenant instance
            reason: Deletion reason
            previous_status: Status before deletion
        """
        try:
            # Convert enum to TenantEventStatus for event
            event_previous_status = TenantEventStatus(previous_status)

            # Extract purge_at timestamp from config
            purge_at_str = tenant.config.get("purge_at")
            purge_at = datetime.fromisoformat(purge_at_str) if purge_at_str else None

            # Create structured event
            event = create_tenant_deleted_event(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                reason=reason,
                previous_status=event_previous_status,
                deleted_at=tenant.deleted_at,
                purge_at=purge_at,
                source_service="registry-service",
                tenant_context_id=None,  # Use None for system context
            )

            # Publish the event
            await self._event_publisher.publish(event, topic="tenant.lifecycle")

            logger.info(
                "tenant_deleted_event_published",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                reason=reason,
                deleted_at=tenant.deleted_at.isoformat() if tenant.deleted_at else None,
                purge_at=purge_at_str,
            )

        except Exception as e:
            logger.error(
                "tenant_deleted_event_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                error=str(e),
                message="Tenant deletion event failed, but tenant was deleted successfully",
            )
            # Don't raise - event publishing failure shouldn't block deletion

    async def _emit_tenant_purge_event(self, tenant: Tenant) -> None:
        """Emit tenant purge event for downstream services.

        This event signals that the tenant and ALL associated data
        must be permanently deleted from all services.

        Args:
            tenant: Tenant instance being purged
        """
        purged_at = datetime.now(UTC).isoformat()

        try:
            await self._event_publisher.publish_tenant_purged(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                tenant_name=tenant.name,
                keycloak_org_id=tenant.keycloak_org_id,
                deleted_at=tenant.deleted_at.isoformat() if tenant.deleted_at else None,
                purged_at=purged_at,
            )
            logger.info(
                "tenant_purged_event_published", tenant_id=tenant.id, tenant_slug=tenant.slug
            )
        except Exception as e:
            logger.error(
                "tenant_purged_event_failed",
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                error=str(e),
            )
            # Don't raise - event publishing failure shouldn't block purge

    async def health_check(self) -> bool:
        """Check if the tenant service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._pool:
                return False

            async with self._pool.acquire() as conn:
                # Simple query to verify connection
                await conn.fetchval("SELECT 1")

            # Verify system tenant exists
            system_tenant = await self.get_system_tenant()
            if not system_tenant or system_tenant.status != TenantStatus.ACTIVE:
                return False

            return True

        except Exception as e:
            logger.error("tenant_service_health_check_failed", error=str(e))
            return False
