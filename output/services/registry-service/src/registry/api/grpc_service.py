"""gRPC service implementation for Registry Service.

This module provides the gRPC API implementation for high-performance
service registration and discovery.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import grpc

from registry.consul_client import ConsulOperationError
from registry.grpc import (
    DeregisterRequest,
    DeregisterResponse,
    DiscoverRequest,
    DiscoverResponse,
    GetHealthRequest,
    GetHealthResponse,
    GetServiceHealthRequest,
    GetServiceHealthResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    InstanceHealthCount,
    InstanceHealthDetail,
    ListServicesRequest,
    ListServicesResponse,
    RegisterRequest,
    RegisterResponse,
    RegistryServiceServicer,
    ServiceEvent,
    ServiceHealthSummary,
    ServiceSummary,
    WatchRequest,
)
from registry.grpc import (
    ServiceInstance as GrpcServiceInstance,
)
from registry.models import (
    HealthCheckConfig,
    HealthStatus,
    Protocol,
    ServiceRegistration,
)
from registry.service import RegistryService

logger = logging.getLogger(__name__)


class RegistryGrpcService(RegistryServiceServicer):
    """gRPC implementation of the Registry Service.

    Provides high-performance RPC interface for service registration,
    discovery, and health monitoring.
    """

    def __init__(self, registry_service: RegistryService):
        """Initialize gRPC service.

        Args:
            registry_service: The core registry service instance.
        """
        self.registry = registry_service
        self._event_subscribers: dict[str, asyncio.Queue] = {}

    async def Register(
        self,
        request: RegisterRequest,
        context: grpc.ServicerContext,
    ) -> RegisterResponse:
        """Register a service instance.

        Args:
            request: Registration request with service details.
            context: gRPC context for setting status codes.

        Returns:
            RegisterResponse with registration details.
        """
        try:
            # Validate request
            if not request.name:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Service name is required")
                return RegisterResponse()

            if not request.version:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Service version is required")
                return RegisterResponse()

            # Build health check config
            health_check = HealthCheckConfig(
                http_endpoint=request.health_check.http_endpoint or None,
                grpc_service=request.health_check.grpc_service or None,
                tcp_address=request.health_check.tcp_address or None,
                interval_seconds=request.health_check.interval_seconds or 10,
                timeout_seconds=request.health_check.timeout_seconds or 5,
                deregister_after_seconds=request.health_check.deregister_after_seconds or 60,
            )

            # Convert protocol
            protocol = Protocol.HTTP
            if request.protocol:
                try:
                    protocol = Protocol(request.protocol.lower())
                except ValueError:
                    protocol = Protocol.HTTP

            # Build registration
            registration = ServiceRegistration(
                name=request.name,
                version=request.version,
                instance_id=request.instance_id,
                address=request.address,
                port=request.port,
                protocol=protocol,
                depends=list(request.depends),
                provides=dict(request.provides.apis) if request.provides else {},
                health_check=health_check,
                tags=list(request.tags),
                metadata=dict(request.metadata),
            )

            # Register
            await self.registry.register(registration)

            return RegisterResponse(
                instance_id=registration.instance_id,
                consul_service_id=registration.instance_id,
                registered_at=registration.registered_at.isoformat(),
                health_check_id=f"service:{registration.instance_id}",
            )

        except ConsulOperationError as e:
            logger.error(f"Consul error during registration: {e}")
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(f"Registry backend unavailable: {e}")
            return RegisterResponse()

        except Exception as e:
            logger.exception(f"Unexpected error during registration: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return RegisterResponse()

    async def Deregister(
        self,
        request: DeregisterRequest,
        context: grpc.ServicerContext,
    ) -> DeregisterResponse:
        """Deregister a service instance.

        Args:
            request: Deregistration request.
            context: gRPC context.

        Returns:
            DeregisterResponse with status.
        """
        try:
            await self.registry.deregister(
                instance_id=request.instance_id,
                service_name=request.service_name,
                version=request.version,
                reason=request.reason or "graceful_shutdown",
            )

            return DeregisterResponse(
                success=True,
                deregistered_at=datetime.now(UTC).isoformat(),
            )

        except ConsulOperationError as e:
            logger.error(f"Consul error during deregistration: {e}")
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(f"Registry backend unavailable: {e}")
            return DeregisterResponse(success=False)

        except Exception as e:
            logger.exception(f"Unexpected error during deregistration: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return DeregisterResponse(success=False)

    async def Heartbeat(
        self,
        request: HeartbeatRequest,
        context: grpc.ServicerContext,
    ) -> HeartbeatResponse:
        """Send a heartbeat for an instance.

        Args:
            request: Heartbeat request.
            context: gRPC context.

        Returns:
            HeartbeatResponse with status.
        """
        # In a full implementation, this would update Consul TTL check
        return HeartbeatResponse(
            instance_id=request.instance_id,
            status=request.status or "passing",
            last_heartbeat=datetime.now(UTC).isoformat(),
        )

    async def Discover(
        self,
        request: DiscoverRequest,
        context: grpc.ServicerContext,
    ) -> DiscoverResponse:
        """Discover service instances.

        Args:
            request: Discovery request with filters.
            context: gRPC context.

        Returns:
            DiscoverResponse with matching instances.
        """
        try:
            tags = list(request.tags) if request.tags else None

            instances = await self.registry.discover(
                service_name=request.service_name,
                version_constraint=request.version_constraint or None,
                tags=tags,
                healthy_only=request.healthy_only,
            )

            if not instances:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Service '{request.service_name}' not found")
                return DiscoverResponse()

            # Convert to gRPC instances
            grpc_instances = []
            healthy_count = 0
            for inst in instances:
                grpc_instances.append(
                    GrpcServiceInstance(
                        instance_id=inst.instance_id,
                        address=inst.address,
                        port=inst.port,
                        protocol=inst.protocol.value,
                        version=inst.version,
                        health_status=inst.health_status.value,
                        tags=inst.tags,
                        metadata=inst.metadata,
                    )
                )
                if inst.health_status == HealthStatus.HEALTHY:
                    healthy_count += 1

            return DiscoverResponse(
                service=request.service_name,
                instances=grpc_instances,
                total_instances=len(instances),
                healthy_instances=healthy_count,
            )

        except ConsulOperationError as e:
            logger.error(f"Consul error during discovery: {e}")
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(f"Registry backend unavailable: {e}")
            return DiscoverResponse()

        except Exception as e:
            logger.exception(f"Unexpected error during discovery: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return DiscoverResponse()

    async def Watch(
        self,
        request: WatchRequest,
        context: grpc.ServicerContext,
    ) -> AsyncIterator[ServiceEvent]:
        """Watch for service events.

        This is a server-side streaming RPC that yields events
        as they occur.

        Args:
            request: Watch request with optional service filter.
            context: gRPC context.

        Yields:
            ServiceEvent for each service change.
        """
        service_filter = request.service_name or None

        # Get event iterator from registry
        if hasattr(self.registry, "subscribe_events"):
            events = self.registry.subscribe_events(service_filter)
            for event in events:
                yield ServiceEvent(
                    event_type=event.get("event_type", "unknown"),
                    service_name=event.get("service_name", ""),
                    instance_id=event.get("instance_id", ""),
                    version=event.get("version", ""),
                    timestamp=datetime.now(UTC).isoformat(),
                )
        else:
            # Fallback: no event subscription support
            logger.warning("Registry service does not support event subscription")

    async def ListServices(
        self,
        request: ListServicesRequest,
        context: grpc.ServicerContext,
    ) -> ListServicesResponse:
        """List all registered services.

        Args:
            request: List request with optional tag filter.
            context: gRPC context.

        Returns:
            ListServicesResponse with service summaries.
        """
        try:
            services = await self.registry.list_services()

            # Filter by tags if provided
            tag_filter = list(request.tags) if request.tags else None

            summaries = []
            for name, tags in services.items():
                if tag_filter and not any(t in tags for t in tag_filter):
                    continue

                info = await self.registry.get_service_info(name)
                summaries.append(
                    ServiceSummary(
                        name=name,
                        versions=info.get("versions", []),
                        instance_count=info.get("instance_count", 0),
                        healthy_count=info.get("healthy_count", 0),
                        tags=tags,
                    )
                )

            return ListServicesResponse(
                services=summaries,
                total_services=len(summaries),
            )

        except Exception as e:
            logger.exception(f"Unexpected error listing services: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return ListServicesResponse()

    async def GetHealth(
        self,
        request: GetHealthRequest,
        context: grpc.ServicerContext,
    ) -> GetHealthResponse:
        """Get health overview of all services.

        Args:
            request: Health request.
            context: gRPC context.

        Returns:
            GetHealthResponse with health overview.
        """
        try:
            overview = await self.registry.get_health_overview()

            # Determine overall status
            unhealthy = overview.get("unhealthy_instances", 0)
            total = overview.get("total_instances", 0)

            if total == 0 or unhealthy == 0:
                overall_status = "healthy"
            elif unhealthy == total:
                overall_status = "critical"
            else:
                overall_status = "warning"

            # Build service summaries
            summaries = []
            for name, counts in overview.get("services", {}).items():
                healthy = counts.get("healthy", 0)
                unhealthy_svc = counts.get("unhealthy", 0)

                if unhealthy_svc == 0:
                    status = "healthy"
                elif healthy == 0:
                    status = "critical"
                else:
                    status = "warning"

                summaries.append(
                    ServiceHealthSummary(
                        name=name,
                        status=status,
                        instances=InstanceHealthCount(
                            healthy=healthy,
                            warning=0,
                            critical=unhealthy_svc,
                        ),
                    )
                )

            return GetHealthResponse(
                services=summaries,
                overall_status=overall_status,
                total_instances=total,
                healthy_instances=overview.get("healthy_instances", 0),
            )

        except Exception as e:
            logger.exception(f"Unexpected error getting health: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GetHealthResponse()

    async def GetServiceHealth(
        self,
        request: GetServiceHealthRequest,
        context: grpc.ServicerContext,
    ) -> GetServiceHealthResponse:
        """Get detailed health for a specific service.

        Args:
            request: Service health request.
            context: gRPC context.

        Returns:
            GetServiceHealthResponse with detailed health.
        """
        try:
            instances = await self.registry.discover(
                request.service_name,
                healthy_only=False,
            )

            if not instances:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Service '{request.service_name}' not found")
                return GetServiceHealthResponse()

            # Determine overall status
            statuses = [i.health_status for i in instances]
            if all(s == HealthStatus.HEALTHY for s in statuses):
                status = "healthy"
            elif any(s == HealthStatus.CRITICAL for s in statuses):
                status = "critical"
            else:
                status = "warning"

            # Build instance details
            instance_details = []
            for inst in instances:
                instance_details.append(
                    InstanceHealthDetail(
                        instance_id=inst.instance_id,
                        status=inst.health_status.value,
                        checks=[],  # Would be populated from Consul
                        uptime_seconds=0,
                    )
                )

            return GetServiceHealthResponse(
                service=request.service_name,
                status=status,
                instances=instance_details,
            )

        except Exception as e:
            logger.exception(f"Unexpected error getting service health: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {type(e).__name__}")
            return GetServiceHealthResponse()


async def serve(
    registry_service: RegistryService,
    port: int = 50051,
) -> grpc.aio.Server:
    """Start the gRPC server.

    Args:
        registry_service: The core registry service.
        port: Port to listen on.

    Returns:
        The running gRPC server.
    """
    from registry.grpc import add_RegistryServiceServicer_to_server

    server = grpc.aio.server()
    grpc_service = RegistryGrpcService(registry_service)
    add_RegistryServiceServicer_to_server(grpc_service, server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info(f"gRPC server started on port {port}")
    return server
