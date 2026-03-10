"""Generated Permission model for VentureStrat.

This module defines the Permission model using VentureStrat BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Permission(BaseModel):
    """Granular permission for resource access control"""

    _name = "aut_permission"
    _schema = "auth"
    _table = "aut_permission"
    _description = "Granular permission for resource access control"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    resource: str = fields.String(
        size=100, required=True, help="Resource name (e.g. trade, position, risk)"
    )
    action: str = fields.String(
        size=50, required=True, help="Action type (e.g. create, read, update, delete, approve)"
    )
    code: str = fields.String(
        size=100, required=True, unique=True, help="Unique permission code (e.g. trade:create)"
    )
    description: str = fields.Text(required=False, help="Human-readable permission description")
    service_name: str = fields.String(
        size=100, required=False, help="Service this permission applies to"
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
