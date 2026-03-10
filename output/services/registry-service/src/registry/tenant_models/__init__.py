"""Registry Service Data Models.

This package defines the core data models for the Registry Service,
including service registration, discovery, health management, and tenant management.
"""

# New models
from .tenant import Tenant, TenantStatus

__all__ = [
    "Tenant",
    "TenantStatus",
]
