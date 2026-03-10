"""gRPC service implementation for Tenant Management.

This module provides the gRPC API implementation for tenant CRUD operations,
status management, quota management, and data export functionality.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Optional

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from registry.export_service import TenantExportService
from registry.grpc.tenant_pb2 import (
    # Requests
    CreateTenantRequest,
    DeleteTenantRequest,
    ExportStatusResponse,
    ExportTenantDataRequest,
    ExportTenantDataResponse,
    GetExportStatusRequest,
    GetTenantBySlugRequest,
    GetTenantQuotasRequest,
    GetTenantRequest,
    # Health Check
    HealthCheckRequest,
    HealthCheckResponse,
    ListTenantsRequest,
    ListTenantsResponse,
    QuotaInfo,
    ResumeTenantRequest,
    SuspendTenantRequest,
    TenantChangeEvent,
    TenantQuotasResponse,
    TenantStatus,
    UpdateTenantQuotasRequest,
    UpdateTenantRequest,
    WatchTenantChangesRequest,
)
from registry.grpc.tenant_pb2 import (
    # Messages
    Tenant as GrpcTenant,
)
from registry.grpc.tenant_pb2_grpc import HealthServicer, TenantServiceServicer
from registry.middleware.quota import RedisQuotaManager
from registry.models.tenant import Tenant as TenantModel
from registry.models.tenant import TenantStatus as TenantStatusEnum
from registry.tenant_service import TenantService

logger = logging.getLogger(__name__)


class TenantGrpcService(TenantServiceServicer):
    """gRPC implementation of the Tenant Service.

    Provides high-performance RPC interface for tenant management,
    including CRUD operations, status management, and data export.
    """

    def __init__(
        self,
        tenant_service: TenantService,
        export_service: Optional[TenantExportService] = None,
        quota_service: Optional[RedisQuotaManager] = None,
    ):
        """Initialize gRPC service.

        Args:
            tenant_service: The core tenant service instance.
            export_service: Optional export service for data export operations.
            quota_service: Optional quota manager for quota management.
        """
        self.tenant_service = tenant_service
        self.export_service = export_service
        self.quota_service = quota_service
        self._change_subscribers: dict[str, asyncio.Queue] = {}

    def _tenant_model_to_grpc(self, tenant: TenantModel) -> GrpcTenant:
        """Convert TenantModel to gRPC Tenant message.

        Args:
            tenant: The tenant model instance

        Returns:
            GrpcTenant message
        """
        # Convert status enum
        if tenant.status == TenantStatusEnum.ACTIVE:
            status = TenantStatus.TENANT_STATUS_ACTIVE
        elif tenant.status == TenantStatusEnum.SUSPENDED:
            status = TenantStatus.TENANT_STATUS_SUSPENDED
        elif tenant.status == TenantStatusEnum.DELETED:
            status = TenantStatus.TENANT_STATUS_DELETED
        else:
            status = TenantStatus.TENANT_STATUS_UNKNOWN

        # Convert timestamps
        created_at = Timestamp()
        created_at.FromDatetime(tenant.created_at)

        updated_at = Timestamp()
        updated_at.FromDatetime(tenant.updated_at)

        # Build gRPC tenant
        grpc_tenant = GrpcTenant(
            id=tenant.id,
            slug=tenant.slug,
            name=tenant.name,
            status=status,
            config=tenant.config or {},
            created_at=created_at,
            updated_at=updated_at,
            created_by="",  # TODO: Add user tracking
        )

        # Optional fields
        if tenant.keycloak_org_id:
            grpc_tenant.keycloak_org_id = tenant.keycloak_org_id

        if tenant.deleted_at:
            deleted_at = Timestamp()
            deleted_at.FromDatetime(tenant.deleted_at)
            grpc_tenant.deleted_at.CopyFrom(deleted_at)

        return grpc_tenant

    async def CreateTenant(
        self,
        request: CreateTenantRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Create a new tenant.

        Args:
            request: Tenant creation request
            context: gRPC context for setting status codes

        Returns:
            Created tenant as gRPC message
        """
        try:
            # Validate request
            if not request.slug:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant slug is required")
                return GrpcTenant()

            if not request.name:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant name is required")
                return GrpcTenant()

            # Validate slug format
            if not self._is_valid_slug(request.slug):
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(
                    "Invalid slug format. Must be lowercase alphanumeric with dashes, start and end with alphanumeric"
                )
                return GrpcTenant()

            # Create tenant
            tenant = await self.tenant_service.create_tenant(
                slug=request.slug,
                name=request.name,
                config=dict(request.config) if request.config else None,
                admin_email=request.admin_email or None,
            )

            logger.info(
                "grpc_tenant_created", tenant_id=tenant.id, slug=tenant.slug, name=tenant.name
            )

            return self._tenant_model_to_grpc(tenant)

        except ValueError as e:
            logger.error(
                "grpc_create_tenant_validation_error",
                slug=request.slug,
                name=request.name,
                error=str(e),
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GrpcTenant()

        except Exception as e:
            logger.exception(
                "grpc_create_tenant_error", slug=request.slug, name=request.name, error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def GetTenant(
        self,
        request: GetTenantRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Get a tenant by ID.

        Args:
            request: Get tenant request
            context: gRPC context

        Returns:
            Tenant as gRPC message
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return GrpcTenant()

            # Validate UUID format
            try:
                uuid.UUID(request.tenant_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid tenant ID format")
                return GrpcTenant()

            tenant = await self.tenant_service.get_tenant_by_id(request.tenant_id)

            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return GrpcTenant()

            return self._tenant_model_to_grpc(tenant)

        except Exception as e:
            logger.exception("grpc_get_tenant_error", tenant_id=request.tenant_id, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def GetTenantBySlug(
        self,
        request: GetTenantBySlugRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Get a tenant by slug.

        Args:
            request: Get tenant by slug request
            context: gRPC context

        Returns:
            Tenant as gRPC message
        """
        try:
            if not request.slug:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant slug is required")
                return GrpcTenant()

            tenant = await self.tenant_service.get_tenant_by_slug(request.slug)

            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with slug '{request.slug}' not found")
                return GrpcTenant()

            return self._tenant_model_to_grpc(tenant)

        except Exception as e:
            logger.exception("grpc_get_tenant_by_slug_error", slug=request.slug, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def UpdateTenant(
        self,
        request: UpdateTenantRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Update a tenant's name or configuration.

        Args:
            request: Update tenant request
            context: gRPC context

        Returns:
            Updated tenant as gRPC message
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return GrpcTenant()

            # Validate UUID format
            try:
                uuid.UUID(request.tenant_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid tenant ID format")
                return GrpcTenant()

            # Prepare update parameters
            name = request.name if request.HasField("name") else None
            config = dict(request.config) if request.config else None

            tenant = await self.tenant_service.update_tenant(
                tenant_id=request.tenant_id, name=name, config=config
            )

            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return GrpcTenant()

            logger.info(
                "grpc_tenant_updated",
                tenant_id=request.tenant_id,
                name=name is not None,
                config=config is not None,
            )

            return self._tenant_model_to_grpc(tenant)

        except ValueError as e:
            logger.error(
                "grpc_update_tenant_validation_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GrpcTenant()

        except Exception as e:
            logger.exception("grpc_update_tenant_error", tenant_id=request.tenant_id, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def DeleteTenant(
        self,
        request: DeleteTenantRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Soft delete a tenant.

        Args:
            request: Delete tenant request
            context: gRPC context

        Returns:
            Deleted tenant as gRPC message
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return GrpcTenant()

            if not request.reason:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Deletion reason is required")
                return GrpcTenant()

            # Validate UUID format
            try:
                uuid.UUID(request.tenant_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid tenant ID format")
                return GrpcTenant()

            tenant = await self.tenant_service.delete_tenant(
                tenant_id=request.tenant_id, reason=request.reason
            )

            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return GrpcTenant()

            logger.info("grpc_tenant_deleted", tenant_id=request.tenant_id, reason=request.reason)

            return self._tenant_model_to_grpc(tenant)

        except ValueError as e:
            logger.error(
                "grpc_delete_tenant_validation_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GrpcTenant()

        except Exception as e:
            logger.exception("grpc_delete_tenant_error", tenant_id=request.tenant_id, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def ListTenants(
        self,
        request: ListTenantsRequest,
        context: grpc.ServicerContext,
    ) -> ListTenantsResponse:
        """List tenants with optional filtering and pagination.

        Args:
            request: List tenants request
            context: gRPC context

        Returns:
            List of tenants response
        """
        try:
            # Validate page_size
            page_size = request.page_size or 50
            if page_size <= 0 or page_size > 100:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Page size must be between 1 and 100")
                return ListTenantsResponse()

            # TODO: Implement proper pagination token handling
            page = 1  # For now, use simple page numbering

            # Get optional filters
            status = request.status if request.HasField("status") else None
            search = request.search if request.HasField("search") else None

            tenants, total_count = await self.tenant_service.list_tenants(
                status=status, search=search, page=page, page_size=page_size
            )

            # Convert to gRPC tenants
            grpc_tenants = [self._tenant_model_to_grpc(tenant) for tenant in tenants]

            # Generate next page token if there are more results
            next_page_token = ""
            if len(tenants) == page_size:
                # Simple token encoding: just the next page number
                next_page_token = str(page + 1)

            return ListTenantsResponse(
                tenants=grpc_tenants, next_page_token=next_page_token, total_count=total_count
            )

        except Exception as e:
            logger.exception("grpc_list_tenants_error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return ListTenantsResponse()

    async def SuspendTenant(
        self,
        request: SuspendTenantRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Suspend a tenant.

        Args:
            request: Suspend tenant request
            context: gRPC context

        Returns:
            Suspended tenant as gRPC message
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return GrpcTenant()

            if not request.reason:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Suspension reason is required")
                return GrpcTenant()

            # Validate UUID format
            try:
                uuid.UUID(request.tenant_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid tenant ID format")
                return GrpcTenant()

            tenant = await self.tenant_service.suspend_tenant(
                tenant_id=request.tenant_id, reason=request.reason
            )

            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return GrpcTenant()

            logger.info("grpc_tenant_suspended", tenant_id=request.tenant_id, reason=request.reason)

            return self._tenant_model_to_grpc(tenant)

        except ValueError as e:
            logger.error(
                "grpc_suspend_tenant_validation_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GrpcTenant()

        except Exception as e:
            logger.exception("grpc_suspend_tenant_error", tenant_id=request.tenant_id, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def ResumeTenant(
        self,
        request: ResumeTenantRequest,
        context: grpc.ServicerContext,
    ) -> GrpcTenant:
        """Resume a suspended tenant.

        Args:
            request: Resume tenant request
            context: gRPC context

        Returns:
            Resumed tenant as gRPC message
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return GrpcTenant()

            # Validate UUID format
            try:
                uuid.UUID(request.tenant_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid tenant ID format")
                return GrpcTenant()

            tenant = await self.tenant_service.resume_tenant(tenant_id=request.tenant_id)

            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return GrpcTenant()

            logger.info("grpc_tenant_resumed", tenant_id=request.tenant_id)

            return self._tenant_model_to_grpc(tenant)

        except ValueError as e:
            logger.error(
                "grpc_resume_tenant_validation_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GrpcTenant()

        except Exception as e:
            logger.exception("grpc_resume_tenant_error", tenant_id=request.tenant_id, error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GrpcTenant()

    async def ExportTenantData(
        self,
        request: ExportTenantDataRequest,
        context: grpc.ServicerContext,
    ) -> ExportTenantDataResponse:
        """Start a tenant data export job for GDPR compliance.

        Args:
            request: Export tenant data request
            context: gRPC context

        Returns:
            Export job status response
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return ExportTenantDataResponse()

            # Validate UUID format
            try:
                uuid.UUID(request.tenant_id)
            except ValueError:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid tenant ID format")
                return ExportTenantDataResponse()

            # Check if export service is available
            if not self.export_service:
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details("Export service not available")
                return ExportTenantDataResponse()

            # Verify tenant exists
            tenant = await self.tenant_service.get_tenant_by_id(request.tenant_id)
            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return ExportTenantDataResponse()

            # Start export job
            data_types = list(request.data_types) if request.data_types else None
            export_format = request.format if request.format else "json"

            export_job = await self.export_service.start_export(
                tenant_id=request.tenant_id, data_types=data_types, export_format=export_format
            )

            # Convert estimated completion time
            estimated_completion = Timestamp()
            estimated_completion.FromDatetime(export_job.estimated_completion)

            logger.info(
                "grpc_tenant_export_started",
                tenant_id=request.tenant_id,
                export_id=export_job.export_id,
                data_types=data_types,
                format=export_format,
            )

            return ExportTenantDataResponse(
                export_id=export_job.export_id,
                status=export_job.status,
                estimated_completion=estimated_completion,
            )

        except Exception as e:
            logger.exception(
                "grpc_export_tenant_data_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return ExportTenantDataResponse()

    async def GetExportStatus(
        self,
        request: GetExportStatusRequest,
        context: grpc.ServicerContext,
    ) -> ExportStatusResponse:
        """Get the status of a tenant data export job.

        Args:
            request: Get export status request
            context: gRPC context

        Returns:
            Export status response
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return ExportStatusResponse()

            if not request.export_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Export ID is required")
                return ExportStatusResponse()

            # Check if export service is available
            if not self.export_service:
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details("Export service not available")
                return ExportStatusResponse()

            export_job = await self.export_service.get_export_status(
                tenant_id=request.tenant_id, export_id=request.export_id
            )

            if not export_job:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(
                    f"Export job '{request.export_id}' not found for tenant '{request.tenant_id}'"
                )
                return ExportStatusResponse()

            response = ExportStatusResponse(
                export_id=export_job.export_id, status=export_job.status
            )

            # Add optional fields based on status
            if export_job.status == "completed" and export_job.download_url:
                response.download_url = export_job.download_url
                if export_job.expires_at:
                    expires_at = Timestamp()
                    expires_at.FromDatetime(export_job.expires_at)
                    response.expires_at.CopyFrom(expires_at)

            if export_job.status == "failed" and export_job.error_message:
                response.error_message = export_job.error_message

            return response

        except Exception as e:
            logger.exception(
                "grpc_get_export_status_error",
                tenant_id=request.tenant_id,
                export_id=request.export_id,
                error=str(e),
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return ExportStatusResponse()

    async def GetTenantQuotas(
        self,
        request: GetTenantQuotasRequest,
        context: grpc.ServicerContext,
    ) -> TenantQuotasResponse:
        """Get tenant quota information.

        Args:
            request: Get tenant quotas request
            context: gRPC context

        Returns:
            Tenant quotas response
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return TenantQuotasResponse()

            # Check if quota service is available
            if not self.quota_service:
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details("Quota service not available")
                return TenantQuotasResponse()

            # Verify tenant exists
            tenant = await self.tenant_service.get_tenant_by_id(request.tenant_id)
            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return TenantQuotasResponse()

            quotas = await self.quota_service.get_tenant_quotas(request.tenant_id)

            # Convert to gRPC quota info
            grpc_quotas = {}
            for resource, info in quotas.items():
                grpc_quotas[resource] = QuotaInfo(
                    limit=info.limit, current=info.current, usage_percentage=info.usage_percentage
                )

            return TenantQuotasResponse(tenant_id=request.tenant_id, quotas=grpc_quotas)

        except Exception as e:
            logger.exception(
                "grpc_get_tenant_quotas_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return TenantQuotasResponse()

    async def UpdateTenantQuotas(
        self,
        request: UpdateTenantQuotasRequest,
        context: grpc.ServicerContext,
    ) -> TenantQuotasResponse:
        """Update tenant quota limits.

        Args:
            request: Update tenant quotas request
            context: gRPC context

        Returns:
            Updated tenant quotas response
        """
        try:
            if not request.tenant_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Tenant ID is required")
                return TenantQuotasResponse()

            if not request.quotas:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("At least one quota must be specified")
                return TenantQuotasResponse()

            # Check if quota service is available
            if not self.quota_service:
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details("Quota service not available")
                return TenantQuotasResponse()

            # Verify tenant exists
            tenant = await self.tenant_service.get_tenant_by_id(request.tenant_id)
            if not tenant:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tenant with ID '{request.tenant_id}' not found")
                return TenantQuotasResponse()

            # Update quotas
            quota_updates = dict(request.quotas)
            await self.quota_service.update_tenant_quotas(request.tenant_id, quota_updates)

            # Get updated quotas
            updated_quotas = await self.quota_service.get_tenant_quotas(request.tenant_id)

            # Convert to gRPC quota info
            grpc_quotas = {}
            for resource, info in updated_quotas.items():
                grpc_quotas[resource] = QuotaInfo(
                    limit=info.limit, current=info.current, usage_percentage=info.usage_percentage
                )

            logger.info(
                "grpc_tenant_quotas_updated",
                tenant_id=request.tenant_id,
                updated_quotas=list(quota_updates.keys()),
            )

            return TenantQuotasResponse(tenant_id=request.tenant_id, quotas=grpc_quotas)

        except ValueError as e:
            logger.error(
                "grpc_update_tenant_quotas_validation_error",
                tenant_id=request.tenant_id,
                error=str(e),
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return TenantQuotasResponse()

        except Exception as e:
            logger.exception(
                "grpc_update_tenant_quotas_error", tenant_id=request.tenant_id, error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return TenantQuotasResponse()

    async def WatchTenantChanges(
        self,
        request: WatchTenantChangesRequest,
        context: grpc.ServicerContext,
    ) -> AsyncIterator[TenantChangeEvent]:
        """Watch for tenant change events.

        This is a server-side streaming RPC that yields events
        as tenant changes occur.

        Args:
            request: Watch request with optional tenant filter
            context: gRPC context

        Yields:
            TenantChangeEvent for each tenant change
        """
        tenant_filter = request.tenant_id if request.HasField("tenant_id") else None

        # Create a unique subscriber ID
        subscriber_id = str(uuid.uuid4())
        event_queue = asyncio.Queue()
        self._change_subscribers[subscriber_id] = event_queue

        try:
            logger.info(
                "grpc_watch_tenant_changes_started",
                subscriber_id=subscriber_id,
                tenant_filter=tenant_filter,
            )

            # For now, this is a placeholder implementation
            # In a real system, this would connect to an event bus/stream
            while True:
                try:
                    # Wait for events with a timeout to allow for graceful shutdown
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)

                    # Filter by tenant if specified
                    if tenant_filter and event.get("tenant_id") != tenant_filter:
                        continue

                    # Convert to gRPC event
                    timestamp = Timestamp()
                    timestamp.FromDatetime(event.get("timestamp", datetime.now(UTC)))

                    yield TenantChangeEvent(
                        event_type=event.get("event_type", TenantChangeEvent.EventType.UNKNOWN),
                        tenant=self._tenant_model_to_grpc(event["tenant"])
                        if "tenant" in event
                        else GrpcTenant(),
                        change_token=event.get("change_token", str(uuid.uuid4())),
                        timestamp=timestamp,
                        changed_by=event.get("changed_by", ""),
                        reason=event.get("reason", ""),
                    )

                except TimeoutError:
                    # Send a keep-alive or check if client is still connected
                    continue

                except Exception as e:
                    logger.error(
                        "grpc_watch_tenant_changes_event_error",
                        subscriber_id=subscriber_id,
                        error=str(e),
                    )
                    break

        except Exception as e:
            logger.exception(
                "grpc_watch_tenant_changes_error", subscriber_id=subscriber_id, error=str(e)
            )
        finally:
            # Clean up subscriber
            self._change_subscribers.pop(subscriber_id, None)
            logger.info("grpc_watch_tenant_changes_ended", subscriber_id=subscriber_id)

    def _is_valid_slug(self, slug: str) -> bool:
        """Validate tenant slug format.

        Args:
            slug: The slug to validate

        Returns:
            True if valid slug format
        """
        import re

        if not slug:
            return False

        # Must be 1-63 characters
        if len(slug) < 1 or len(slug) > 63:
            return False

        # Single character can only be alphanumeric
        if len(slug) == 1:
            return slug.isalnum() and slug.islower()

        # Multi-character: start and end with alphanumeric, middle can have dashes
        pattern = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"
        return bool(re.match(pattern, slug))


class TenantHealthService(HealthServicer):
    """gRPC Health Check service for Tenant Service.

    Implements the standard gRPC health checking protocol.
    """

    def __init__(self, tenant_service: TenantService):
        """Initialize health service.

        Args:
            tenant_service: The core tenant service instance.
        """
        self.tenant_service = tenant_service

    async def Check(
        self,
        request: HealthCheckRequest,
        context: grpc.ServicerContext,
    ) -> HealthCheckResponse:
        """Perform a health check.

        Args:
            request: Health check request
            context: gRPC context

        Returns:
            Health check response
        """
        try:
            # Check tenant service health
            if await self.tenant_service.health_check():
                return HealthCheckResponse(status=HealthCheckResponse.ServingStatus.SERVING)
            else:
                return HealthCheckResponse(status=HealthCheckResponse.ServingStatus.NOT_SERVING)

        except Exception as e:
            logger.exception("grpc_health_check_error", error=str(e))
            return HealthCheckResponse(status=HealthCheckResponse.ServingStatus.NOT_SERVING)

    async def Watch(
        self,
        request: HealthCheckRequest,
        context: grpc.ServicerContext,
    ) -> AsyncIterator[HealthCheckResponse]:
        """Watch health status changes.

        Args:
            request: Health check request
            context: gRPC context

        Yields:
            Health check responses as status changes
        """
        # Send initial status
        try:
            if await self.tenant_service.health_check():
                yield HealthCheckResponse(status=HealthCheckResponse.ServingStatus.SERVING)
            else:
                yield HealthCheckResponse(status=HealthCheckResponse.ServingStatus.NOT_SERVING)
        except Exception:
            yield HealthCheckResponse(status=HealthCheckResponse.ServingStatus.NOT_SERVING)

        # For now, just send periodic updates
        # In a real implementation, this would subscribe to health events
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                if await self.tenant_service.health_check():
                    yield HealthCheckResponse(status=HealthCheckResponse.ServingStatus.SERVING)
                else:
                    yield HealthCheckResponse(status=HealthCheckResponse.ServingStatus.NOT_SERVING)

            except Exception as e:
                logger.exception("grpc_health_watch_error", error=str(e))
                yield HealthCheckResponse(status=HealthCheckResponse.ServingStatus.NOT_SERVING)
                break
