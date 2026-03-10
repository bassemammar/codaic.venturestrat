"""API layer for Registry Service."""

from registry.api.exceptions import (
    ConflictError,
    ConsulUnavailableError,
    InternalError,
    NotFoundError,
    RegistryAPIError,
    ValidationError,
)
from registry.api.models import (
    DiscoverResponse,
    ErrorDetail,
    ErrorInfo,
    ErrorResponse,
    HealthCheckDetail,
    HealthInstanceCount,
    HealthOverviewResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    InstanceHealthDetail,
    ListServicesResponse,
    ManifestResponse,
    RegisterRequest,
    RegisterResponse,
    ServiceHealthResponse,
    ServiceHealthSummary,
    ServiceInstanceResponse,
    ServiceSummary,
)
from registry.api.rest import (
    create_app,
    get_registry_service,
    health_router,
    service_router,
    set_registry_service,
)

__all__ = [
    # App and routers
    "create_app",
    "get_registry_service",
    "set_registry_service",
    "service_router",
    "health_router",
    # Exceptions
    "RegistryAPIError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ConsulUnavailableError",
    "InternalError",
    # Request models
    "RegisterRequest",
    "HeartbeatRequest",
    # Response models
    "RegisterResponse",
    "HeartbeatResponse",
    "ServiceInstanceResponse",
    "DiscoverResponse",
    "ServiceSummary",
    "ListServicesResponse",
    "ManifestResponse",
    "HealthCheckDetail",
    "InstanceHealthDetail",
    "ServiceHealthResponse",
    "HealthInstanceCount",
    "ServiceHealthSummary",
    "HealthOverviewResponse",
    # Error models
    "ErrorDetail",
    "ErrorResponse",
    "ErrorInfo",
]
