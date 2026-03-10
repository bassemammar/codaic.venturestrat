"""Generated Role model for VentureStrat.

This module defines the Role model using VentureStrat BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Role(BaseModel):
    """Authorization role with JSON permissions"""

    _name = "aut_role"
    _schema = "auth"
    _table = "aut_role"
    _description = "Authorization role with JSON permissions"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(size=100, required=True, help="Human-readable role name")
    code: str = fields.String(
        size=50, required=True, unique=True, help="Unique role code (e.g. admin, trader, viewer)"
    )
    description: str = fields.Text(required=False, help="Role description")
    permissions: str = fields.JSON(
        required=False, help="JSON array of permission codes granted to this role"
    )
    is_system: str = fields.Boolean(
        required=True, default=False, help="Whether this is a built-in system role"
    )
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
