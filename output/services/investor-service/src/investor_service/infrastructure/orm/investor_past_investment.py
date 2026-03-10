"""Generated InvestorPastInvestment model for TreasuryOS.

This module defines the InvestorPastInvestment model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class InvestorPastInvestment(BaseModel):
    """Many-to-many junction between investors and their past investments"""

    _name = "vs_investor_past_investment"
    _schema = "venturestrat"
    _table = "vs_investor_past_investment"
    _description = "Many-to-many junction between investors and their past investments"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    investor_id: str = fields.Many2one(
        "venturestrat.vs_investor", required=True, ondelete="RESTRICT"
    )
    past_investment_id: str = fields.Many2one(
        "venturestrat.vs_past_investment", required=True, ondelete="RESTRICT"
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
