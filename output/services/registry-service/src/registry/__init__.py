"""VentureStrat Registry Service.

A Consul-based service registry that enables automatic service discovery,
health monitoring, and metadata storage for the VentureStrat platform.
"""

__version__ = "0.1.0"

from registry.consul_client import (
    ConsulClient,
    ConsulConnectionError,
    ConsulOperationError,
)
from registry.events import (
    EventPublisher,
    EventType,
    ServiceDeregisteredEvent,
    ServiceEvent,
    ServiceHealthChangedEvent,
    ServiceRegisteredEvent,
)
from registry.health import (
    HealthCheckResult,
    HealthManager,
    HealthTransition,
)
from registry.manifest import (
    Manifest,
    ManifestParseError,
    ManifestParser,
    ManifestValidationError,
)
from registry.models import (
    HealthCheckConfig,
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceQuery,
    ServiceRegistration,
    Tenant,
    TenantStatus,
)
from registry.service import RegistryService
from registry.version import (
    VersionConstraintError,
    VersionMatcher,
)

__all__ = [
    # Manifest
    "Manifest",
    "ManifestParser",
    "ManifestParseError",
    "ManifestValidationError",
    # Models
    "HealthCheckConfig",
    "HealthStatus",
    "Protocol",
    "ServiceInstance",
    "ServiceQuery",
    "ServiceRegistration",
    "Tenant",
    "TenantStatus",
    # Version
    "VersionConstraintError",
    "VersionMatcher",
    # Consul
    "ConsulClient",
    "ConsulConnectionError",
    "ConsulOperationError",
    # Health
    "HealthManager",
    "HealthCheckResult",
    "HealthTransition",
    # Events
    "EventPublisher",
    "EventType",
    "ServiceEvent",
    "ServiceRegisteredEvent",
    "ServiceDeregisteredEvent",
    "ServiceHealthChangedEvent",
    # Service
    "RegistryService",
]
