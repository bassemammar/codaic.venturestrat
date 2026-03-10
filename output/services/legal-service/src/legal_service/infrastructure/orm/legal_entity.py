"""Generated LegalEntity model.

This module defines the LegalEntity model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class LegalEntity(BaseModel):
    """Legal entity (company or organization) that acts as party in legal documents"""

    _name = "vs_legal_entity"
    _schema = "venturestrat"
    _table = "vs_legal_entity"
    _description = "Legal entity (company or organization) that acts as party in legal documents"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True, help="Auth user who created this entity")
    legal_name: str = fields.String(
        size=200, required=True, help="Registered legal name of the entity"
    )
    jurisdiction: str = fields.String(
        size=30, required=True, help="Legal jurisdiction of incorporation"
    )
    registration_number: str = fields.String(
        size=50, required=True, help="Company registration or incorporation number"
    )
    incorporation_date: str = fields.Date(required=False)
    authorized_shares: str = fields.Integer(
        required=False, help="Total authorized shares (null if unlimited or N/A)"
    )
    par_value: str = fields.Decimal(required=False, help="Par value per share")
    registered_address_id: str = fields.Many2one(
        "venturestrat.vs_legal_address",
        required=False,
        ondelete="RESTRICT",
        help="Registered office address",
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
