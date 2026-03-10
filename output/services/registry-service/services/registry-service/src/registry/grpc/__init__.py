"""gRPC generated code for Registry Service."""

from registry.grpc.registry_pb2 import (
    DeregisterRequest,
    DeregisterResponse,
    DiscoverRequest,
    DiscoverResponse,
    # Health messages
    GetHealthRequest,
    GetHealthResponse,
    GetServiceHealthRequest,
    GetServiceHealthResponse,
    HealthCheck,
    # Registration messages
    HealthCheckConfig,
    HeartbeatRequest,
    HeartbeatResponse,
    InstanceHealthCount,
    InstanceHealthDetail,
    ListServicesRequest,
    ListServicesResponse,
    ProvidesConfig,
    RegisterRequest,
    RegisterResponse,
    ServiceEvent,
    ServiceHealthSummary,
    # Discovery messages
    ServiceInstance,
    ServiceSummary,
    WatchRequest,
)
from registry.grpc.registry_pb2_grpc import (
    RegistryServiceServicer,
    RegistryServiceStub,
    add_RegistryServiceServicer_to_server,
)

# Tenant Service - gRPC API
from registry.grpc.tenant_pb2 import (
    # Request/Response Messages
    CreateTenantRequest,
    DeleteTenantRequest,
    ExportStatusResponse,
    ExportTenantDataRequest,
    ExportTenantDataResponse,
    GetExportStatusRequest,
    GetTenantBySlugRequest,
    GetTenantQuotasRequest,
    GetTenantRequest,
    ListTenantsRequest,
    ListTenantsResponse,
    QuotaInfo,
    ResumeTenantRequest,
    SuspendTenantRequest,
    # Data Models
    Tenant,
    TenantChangeEvent,
    TenantQuotasResponse,
    TenantStatus,
    UpdateTenantQuotasRequest,
    UpdateTenantRequest,
    WatchTenantChangesRequest,
)
from registry.grpc.tenant_pb2 import (
    # Health Messages (from tenant proto)
    HealthCheckRequest as TenantHealthCheckRequest,
)
from registry.grpc.tenant_pb2 import (
    HealthCheckResponse as TenantHealthCheckResponse,
)
from registry.grpc.tenant_pb2_grpc import (
    HealthServicer as TenantHealthServicer,
)
from registry.grpc.tenant_pb2_grpc import (
    HealthStub as TenantHealthStub,
)
from registry.grpc.tenant_pb2_grpc import (
    TenantServiceServicer,
    TenantServiceStub,
    add_TenantServiceServicer_to_server,
)
from registry.grpc.tenant_pb2_grpc import (
    add_HealthServicer_to_server as add_TenantHealthServicer_to_server,
)

__all__ = [
    # Registration messages
    "HealthCheckConfig",
    "ProvidesConfig",
    "RegisterRequest",
    "RegisterResponse",
    "DeregisterRequest",
    "DeregisterResponse",
    "HeartbeatRequest",
    "HeartbeatResponse",
    # Discovery messages
    "ServiceInstance",
    "DiscoverRequest",
    "DiscoverResponse",
    "WatchRequest",
    "ServiceEvent",
    "ListServicesRequest",
    "ServiceSummary",
    "ListServicesResponse",
    # Health messages
    "GetHealthRequest",
    "InstanceHealthCount",
    "ServiceHealthSummary",
    "GetHealthResponse",
    "GetServiceHealthRequest",
    "HealthCheck",
    "InstanceHealthDetail",
    "GetServiceHealthResponse",
    # gRPC service
    "RegistryServiceServicer",
    "RegistryServiceStub",
    "add_RegistryServiceServicer_to_server",
    # Tenant Service - Request/Response Messages
    "CreateTenantRequest",
    "GetTenantRequest",
    "GetTenantBySlugRequest",
    "UpdateTenantRequest",
    "DeleteTenantRequest",
    "ListTenantsRequest",
    "ListTenantsResponse",
    "SuspendTenantRequest",
    "ResumeTenantRequest",
    "ExportTenantDataRequest",
    "ExportTenantDataResponse",
    "GetExportStatusRequest",
    "ExportStatusResponse",
    "GetTenantQuotasRequest",
    "UpdateTenantQuotasRequest",
    "TenantQuotasResponse",
    "WatchTenantChangesRequest",
    "TenantChangeEvent",
    # Tenant Service - Data Models
    "Tenant",
    "TenantStatus",
    "QuotaInfo",
    # Tenant Service - Health Messages
    "TenantHealthCheckRequest",
    "TenantHealthCheckResponse",
    # Tenant Service - gRPC Service
    "TenantServiceServicer",
    "TenantServiceStub",
    "add_TenantServiceServicer_to_server",
    "TenantHealthServicer",
    "TenantHealthStub",
    "add_TenantHealthServicer_to_server",
]
