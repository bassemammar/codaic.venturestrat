"""Generated LegalAddress model.

This module defines the LegalAddress model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class LegalAddress(BaseModel):
    """Physical address for legal entities and persons with jurisdiction classification"""

    _name = "vs_legal_address"
    _schema = "venturestrat"
    _table = "vs_legal_address"
    _description = (
        "Physical address for legal entities and persons with jurisdiction classification"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    address_line_1: str = fields.String(size=100, required=True)
    address_line_2: str = fields.String(size=100, required=False)
    city: str = fields.String(size=50, required=True)
    state_province: str = fields.String(size=50, required=False)
    postal_code: str = fields.String(size=20, required=True)
    country: str = fields.String(size=2, required=True, help="ISO 3166-1 alpha-2 country code")
    jurisdiction: str = fields.String(size=30, required=True)
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
