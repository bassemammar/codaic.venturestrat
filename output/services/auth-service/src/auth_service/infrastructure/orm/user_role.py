"""Generated UserRole model for VentureStrat.

This module defines the UserRole model using VentureStrat BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class UserRole(BaseModel):
    """Many-to-many mapping between users and roles"""

    _name = "aut_user_role"
    _schema = "auth"
    _table = "aut_user_role"
    _description = "Many-to-many mapping between users and roles"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=255, required=True, help="User assigned to this role")
    role_id: str = fields.String(size=255, required=True, help="Role assigned to user")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
