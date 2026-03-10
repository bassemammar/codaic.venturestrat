"""Generated User model for VentureStrat.

This module defines the User model using VentureStrat BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class User(BaseModel):
    """System user with authentication credentials"""

    _name = "aut_user"
    _schema = "auth"
    _table = "aut_user"
    _description = "System user with authentication credentials"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    username: str = fields.String(
        size=100, required=True, unique=True, help="Unique login username"
    )
    email: str = fields.String(size=255, required=True, unique=True, help="User email address")
    hashed_password: str = fields.String(size=255, required=True, help="Bcrypt hashed password")
    first_name: str = fields.String(size=100, required=False, help="User first name")
    last_name: str = fields.String(size=100, required=False, help="User last name")
    is_active: str = fields.Boolean(
        required=True, default=True, help="Whether user account is active"
    )
    last_login: str = fields.DateTime(required=False, help="Timestamp of last successful login")
    failed_login_count: str = fields.Integer(
        required=True, default=0, help="Number of consecutive failed login attempts"
    )
    locked_until: str = fields.DateTime(required=False, help="Account locked until this timestamp")
    default_tenant_id: str = fields.String(
        size=255, required=False, help="Default tenant for this user"
    )
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    # Soft-delete timestamp (None = active, set = soft-deleted)
    deleted_at: Optional[datetime] = fields.DateTime(
        required=False,
        readonly=True,
        default=None,
        help="Soft-delete timestamp. When set, record is excluded from normal queries.",
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
