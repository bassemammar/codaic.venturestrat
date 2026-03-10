"""Generated ContactPerson model.

This module defines the ContactPerson model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class ContactPerson(BaseModel):
    """Individual associated with a legal entity — founder, director, signatory, or counterparty"""

    _name = "vs_contact_person"
    _schema = "venturestrat"
    _table = "vs_contact_person"
    _description = (
        "Individual associated with a legal entity — founder, director, signatory, or counterparty"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True, help="Auth user who created this person")
    legal_entity_id: str = fields.Many2one(
        "venturestrat.vs_legal_entity",
        required=False,
        ondelete="RESTRICT",
        help="Company this person belongs to (null for independent counterparties)",
    )
    full_name: str = fields.String(size=100, required=True)
    email: str = fields.String(size=255, required=True)
    role: str = fields.String(size=20, required=True)
    is_primary: str = fields.Boolean(
        required=True,
        default=False,
        help="Whether this is the primary contact for the legal entity",
    )
    date_of_birth: str = fields.Date(required=False)
    residential_address_id: str = fields.Many2one(
        "venturestrat.vs_legal_address", required=False, ondelete="RESTRICT"
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
