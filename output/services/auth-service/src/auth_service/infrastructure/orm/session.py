"""Generated Session model for VentureStrat.

This module defines the Session model using VentureStrat BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Session(BaseModel):
    """Active user session with token tracking"""

    _name = "aut_session"
    _schema = "auth"
    _table = "aut_session"
    _description = "Active user session with token tracking"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=255, required=True, help="User who owns this session")
    token_hash: str = fields.String(size=255, required=True, help="SHA256 hash of the access token")
    refresh_token_hash: str = fields.String(
        size=255, required=False, help="SHA256 hash of the refresh token"
    )
    ip_address: str = fields.String(size=45, required=False, help="Client IP address")
    user_agent: str = fields.String(size=500, required=False, help="Client user agent string")
    is_active: str = fields.Boolean(
        required=True, default=True, help="Whether session is still active"
    )
    expires_at: str = fields.DateTime(required=True, help="When this session expires")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
