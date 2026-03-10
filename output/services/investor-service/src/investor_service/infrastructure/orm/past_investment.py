"""Generated PastInvestment model for TreasuryOS.

This module defines the PastInvestment model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class PastInvestment(BaseModel):
    """Portfolio company that an investor has previously invested in"""

    _name = "vs_past_investment"
    _schema = "venturestrat"
    _table = "vs_past_investment"
    _description = "Portfolio company that an investor has previously invested in"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    title: str = fields.String(size=255, required=True, unique=True, help="Company name")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
